"""TTS 生成 + 字幕时间轴,适配几何证明视频。

支持两种 TTS provider(自动选择,或显式指定):
  - edge:    Microsoft Edge 免费 TTS(默认,无需 API Key,需联网)
  - minimax: MiniMax TTS(需 minimaxi=<key> 环境变量,质量更好)

输出:
- public/assets/audio/voice.mp3            单条整段音频
- work/audio/generated/                    分段 mp3(按 LINES 缓存)
- work/captions/captions.srt               标准 SRT
- work/captions/captions_aligned.json      每条字幕 start/end/parts (Remotion 时间轴来源)

默认 1.2x 语速,30fps。

使用示例:
  python scripts/generate_tts.py                       # 自动选择 provider
  python scripts/generate_tts.py --provider edge       # 强制用 edge 免费方案
  python scripts/generate_tts.py --provider minimax    # 强制用 MiniMax(需 .env 中配 minimaxi=)
  python scripts/generate_tts.py --list-voices         # 列出 edge 可用中文 voice
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Protocol

import requests

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "public" / "assets" / "audio"
WORK_AUDIO = ROOT / "work" / "audio" / "generated"
WORK_CAP = ROOT / "work" / "captions"
for d in (AUDIO_DIR, WORK_AUDIO, WORK_CAP):
    d.mkdir(parents=True, exist_ok=True)

# === 全局配置 ===
SPEED = 1.2   # 1.2x 语速(两端方案都用这个数)
FPS = 30

# === TTS Provider 抽象 ===
class TTSProvider(Protocol):
    name: str
    def synthesize(self, text: str, out_path: Path) -> None: ...
    def is_configured(self) -> bool: ...
    def describe(self) -> str: ...


# ============ MiniMax Provider ============
class MiniMaxProvider:
    name = "minimax"
    URL = "https://api.minimaxi.com/v1/t2a_v2"
    VOICE_ID = "moss_audio_2ecaeaac-5e5a-11f1-99fb-96e792fde6a1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    def is_configured(self) -> bool:
        return bool(self.api_key) and self.api_key != "your_api_key_here"

    def describe(self) -> str:
        return f"minimax(voice={self.VOICE_ID}, speed={SPEED})"

    def synthesize(self, text: str, out_path: Path) -> None:
        payload = {
            "model": "speech-2.8-hd",
            "text": text,
            "stream": False,
            "voice_setting": {"voice_id": self.VOICE_ID, "speed": SPEED, "vol": 1, "pitch": 0},
            "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
            "output_format": "url",
        }
        r = requests.post(self.URL, json=payload, headers=self.headers, timeout=90).json()
        if r.get("base_resp", {}).get("status_code") != 0:
            raise RuntimeError(f"MiniMax error: {r.get('base_resp', {}).get('status_msg')}")
        ad = r["data"]["audio"]
        body = requests.get(ad, timeout=90).content if ad.startswith("http") else bytes.fromhex(ad)
        out_path.write_bytes(body)


# ============ Edge (Microsoft) Provider ============
class EdgeProvider:
    """edge-tts 免费方案,基于 Microsoft Edge 在线 TTS。无需 API Key,需联网。"""
    name = "edge"
    DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"  # 晓晓(女声,通用,中文推荐)
    # 其他常用中文 voice:
    #   zh-CN-YunxiNeural     云希(男声,通用)
    #   zh-CN-YunyangNeural   云扬(男声,新闻/旁白风格,适合数学证明)
    #   zh-CN-XiaoyiNeural    晓伊(女声,情感丰富)
    #   zh-CN-YunjianNeural   云健(男声,体育解说)
    #   zh-CN-liaoning-XiaobeiNeural  辽宁话(趣味)
    # 列出所有可用 voice: edge-tts --list-voices

    def __init__(self, voice: str | None = None):
        self.voice = voice or self.DEFAULT_VOICE
        # edge-tts rate 格式: "+0%" / "+20%" / "-20%"
        # 1.2x SPEED → "+20%"
        delta_pct = int(round((SPEED - 1.0) * 100))
        sign = "+" if delta_pct >= 0 else ""
        self.rate = f"{sign}{delta_pct}%"

    def is_configured(self) -> bool:
        return True  # 永远可用,只要能联网

    def describe(self) -> str:
        return f"edge(voice={self.voice}, rate={self.rate})"

    def synthesize(self, text: str, out_path: Path) -> None:
        """同步包装 edge-tts 异步 API。"""
        import edge_tts
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        communicate.save_sync(str(out_path))


# ============ Provider 加载 ============
def _load_env_value(key: str) -> str | None:
    """按以下顺序查找 key 的值: 命令行环境 > 项目根 .env > 父级 .env > 祖父 .env。"""
    val = os.environ.get(key)
    if val:
        return val.strip()
    for parent in (ROOT, ROOT.parent, ROOT.parent.parent):
        env_path = parent / ".env"
        if not env_path.exists():
            continue
        m = re.search(rf"^{re.escape(key)}\s*=\s*(\S+)", env_path.read_text(encoding="utf-8"), re.MULTILINE)
        if m and m.group(1) and m.group(1) != "your_api_key_here":
            return m.group(1)
    return None


def _load_minimax_key() -> str | None:
    return _load_env_value("minimaxi")


def _load_tts_provider_pref() -> str | None:
    """读取 TTS_PROVIDER 偏好。可选值: edge | minimax。"""
    return _load_env_value("TTS_PROVIDER")


def _load_edge_voice() -> str | None:
    """读取 EDGE_VOICE 配置。"""
    return _load_env_value("EDGE_VOICE")


def select_provider(arg_provider: str | None, edge_voice: str | None) -> TTSProvider:
    """按优先级选择 provider:
       1. --provider 命令行参数
       2. .env 中 TTS_PROVIDER=xxx
       3. 有 minimaxi=xxx → minimax
       4. 默认 edge
    """
    pref = (arg_provider or _load_tts_provider_pref() or "").lower().strip()
    minimax_key = _load_minimax_key()
    voice = edge_voice or _load_edge_voice()

    if pref == "minimax":
        if not minimax_key:
            raise RuntimeError(
                "指定了 --provider minimax 但未找到 MiniMax API Key。\n"
                "请在 .env 中设置 minimaxi=<your-key>。参考 .env.example。"
            )
        return MiniMaxProvider(minimax_key)

    if pref == "edge":
        return EdgeProvider(voice=voice)

    # 未显式指定: 有 minimax key 优先用,否则 edge
    if minimax_key:
        print(f"  [auto] 检测到 minimaxi=*** → 使用 minimax provider(高质量)")
        return MiniMaxProvider(minimax_key)

    print(f"  [auto] 未配置 MiniMax API Key → 自动回退到 edge 免费方案")
    return EdgeProvider(voice=voice)


# ============ 通用工具 ============
def hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:10]


def measure(p: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, timeout=10,
    )
    return float(out.stdout.strip())


def concat_mp3(parts: list[Path], out: Path) -> None:
    listfile = out.parent / f"{out.stem}.list"
    listfile.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
         "-c", "copy", str(out)],
        check=True, capture_output=True,
    )
    listfile.unlink()


def srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ============ LINES 列表(用户编辑) ============
LINES = [
    {"id": "H01", "chapter": "钩子", "text": "示例字幕: 这里替换为钩子台词。"},
    {"id": "P01", "chapter": "准备", "text": "示例字幕: 这里替换为准备台词。"},
    # ...继续添加
]


# ============ 主流程 ============
def list_edge_voices() -> int:
    """列出 edge-tts 可用中文 voice。"""
    try:
        import edge_tts
    except ImportError:
        print("未安装 edge-tts。运行: pip install edge-tts")
        return 1
    voices = asyncio.run(edge_tts.list_voices())
    print("\n=== edge-tts 中文 voice 列表 ===")
    for v in voices:
        if v["Locale"].startswith("zh-"):
            short = v["ShortName"]
            gender = v["Gender"]
            region = v["Locale"]
            friendly = v.get("FriendlyName", "")
            print(f"  {short:42s}  {region:8s}  {gender:6s}  {friendly}")
    print("\n使用方式: --edge-voice zh-CN-YunyangNeural")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="TTS + 字幕时间轴生成")
    parser.add_argument(
        "--provider",
        choices=["auto", "edge", "minimax"],
        default="auto",
        help="TTS provider(默认 auto: 有 minimax key 优先,否则 edge)",
    )
    parser.add_argument(
        "--edge-voice",
        default=None,
        help=f"edge-tts 中文 voice(默认 {EdgeProvider.DEFAULT_VOICE})",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="列出 edge-tts 可用中文 voice 后退出",
    )
    args = parser.parse_args()

    if args.list_voices:
        sys.exit(list_edge_voices())

    provider = select_provider(args.provider if args.provider != "auto" else None, args.edge_voice)
    print(f"\n[provider] {provider.describe()}\n")

    if not LINES or LINES[0]["text"].startswith("示例字幕"):
        print("⚠️  LINES 仍是占位内容,请先在 scripts/generate_tts.py 里填入真实台词。")
        if "--force" not in sys.argv:
            print("   (如确想跑占位,加 --force)")
            sys.exit(1)

    parts = []
    aligned = []
    srt_entries = []
    cursor = 0.0

    for line in LINES:
        lid = line["id"]
        h = hash_text(f"{provider.name}|{lid}|{line['text']}")
        p = WORK_AUDIO / f"{lid}_{provider.name}_{h}.mp3"
        if not p.exists():
            preview = line["text"][:32].replace("\n", " ")
            print(f"  {lid} {preview}...")
            try:
                provider.synthesize(line["text"], p)
            except Exception as e:
                raise RuntimeError(f"TTS 合成失败({lid}): {e}") from e
            # edge-tts 速率限制: 每请求间隔 0.3s 较稳
            time.sleep(0.3)
        dur = measure(p)
        parts.append(p)
        aligned.append({
            "id": lid,
            "chapter": line["chapter"],
            "start": round(cursor, 3),
            "end": round(cursor + dur, 3),
            "start_frame": int(round(cursor * FPS)),
            "end_frame": int(round((cursor + dur) * FPS)),
            "text": line["text"],
            "file": p.name,
            "provider": provider.name,
        })
        srt_entries.append({
            "index": len(srt_entries) + 1,
            "start": cursor,
            "end": cursor + dur,
            "text": line["text"],
        })
        cursor += dur

    voice_mp3 = AUDIO_DIR / "voice.mp3"
    if len(parts) == 1:
        subprocess.run(["cp", str(parts[0]), str(voice_mp3)], check=True)
    else:
        concat_mp3(parts, voice_mp3)
    total = measure(voice_mp3)

    aligned_obj = {
        "fps": FPS,
        "speed": SPEED,
        "provider": provider.name,
        "voice_mp3": str(voice_mp3.relative_to(ROOT)),
        "total_duration": round(total, 3),
        "total_frames": int(round(total * FPS)),
        "lines": aligned,
    }
    (WORK_CAP / "captions_aligned.json").write_text(
        json.dumps(aligned_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    srt_lines = []
    for e in srt_entries:
        srt_lines.append(str(e["index"]))
        srt_lines.append(f"{srt_time(e['start'])} --> {srt_time(e['end'])}")
        srt_lines.append(e["text"])
        srt_lines.append("")
    (WORK_CAP / "captions.srt").write_text("\n".join(srt_lines), encoding="utf-8")

    print(f"\nTotal: {total:.2f}s ({int(round(total * FPS))} frames @ {FPS}fps)")
    print(f"  voice.mp3          -> {voice_mp3}")
    print(f"  captions_aligned   -> {WORK_CAP / 'captions_aligned.json'}")
    print(f"  captions.srt       -> {WORK_CAP / 'captions.srt'}")


if __name__ == "__main__":
    main()
