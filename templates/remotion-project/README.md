# Remotion Geometry Math Proof Template

> 精准几何风格数学证明视频的 Remotion 4.0 骨架工程。
> 由 `geometry-math-proof-remotion` skill 提供。

---

## 这是什么

**这是一个骨架工程,不是最终视频。** 它演示如何把通用组件(`FormulaPanel`/`CaptionStrip`/`HookOverlay`/`TopBar`)拼起来,实际证明需要修改:

- `src/Proof.tsx` — 几何坐标、CAPTIONS、STEPS、TopBar 信息
- `src/Root.tsx` — `durationInFrames`(用 TTS 真实总帧回写)
- `src/geometry.tsx` — `F` 对象(各章节帧锚点)

---

## 快速开始

### 1. 安装依赖

```bash
npm install
```

⚠️ 用原生 `npm install`,**不要** `rtk npm install`(`rtk` 会翻译成 `npm run install` 报错)。

### 2. 配置 TTS 凭据

```bash
cp .env.example .env
# 编辑 .env 填入 MiniMax API Key
# 获取:https://api.minimaxi.com → 控制台 → API Keys
```

### 3. 准备稿子

`work/source/script.md` 中按"钩子 → 准备 → 推导 1~N → 消项 → 收尾"拆 6~10 章。每章先列 beat checklist,再写 LINES。

### 4. 改 `scripts/generate_tts.py` 的 LINES

```python
LINES = [
    {"id": "H01", "chapter": "钩子", "text": "..."},
    {"id": "P01", "chapter": "准备", "text": "..."},
    # ...
]
```

### 5. 跑 TTS

```bash
pip install -r requirements.txt  # 第一次需要
python scripts/generate_tts.py
```

产出:
- `public/assets/audio/voice.mp3` — 整段配音
- `work/captions/captions_aligned.json` — Remotion 时间轴来源
- `work/captions/captions.srt` — 标准 SRT 字幕

### 6. 回写 F 时间轴

把 `captions_aligned.json` 的 `total_frames` 写到 `src/Root.tsx`:

```tsx
durationInFrames={1500}  // ← 改为 total_frames
```

把每行末帧写到 `src/geometry.tsx` 的 `F` 对象:

```ts
export const F = {
  hook: 0,
  prep: 270,        // ← 准备章节起始帧
  derivation: 540,  // ← 推导章节起始帧
  // ...
  end: 1500,        // ← 改为 total_frames
} as const;
```

### 7. 改 `src/Proof.tsx`

- **几何坐标**:`const A = pt(0,0), B = pt(3,0)…`
- **CAPTIONS**:从 `captions_aligned.json` 拆关键词(标 `tone: 'accent'`)
- **STEPS**:`FormulaStep[]`,`from` 锚到对应章节中段
- **TopBar**:`TOPBAR` 对象的 `series`/`subtitle`/`chapter`/`formula`
- **HookOverlay**:title 用大字公式,attribution 写历史/人物
- **EndingOverlay**:result 用大字结论,attribution 写历史/作者/年代

### 8. 验证循环

```bash
# TS 类型检查
npx tsc --noEmit

# 启动 Studio 实时预览
npm run studio
# 浏览器访问 http://localhost:3000

# 出低分辨率预览版(0.5x,约 4x 快)
npm run render:preview
# → renders/preview-low.mp4
# 用户确认后再出 1080p 成片
npm run render
# → renders/final-1080p.mp4
```

### 9. 静帧抽查(可选但推荐)

```bash
# 渲接近每章结尾的静帧
npx remotion still src/index.ts Proof --frame=<章末帧-30> out/check-N.png
```

读图检查:
- 文字溢出 SVG 框
- 几何元素重叠遮挡
- 字幕压住关键标签
- 公式行列错位

---

## 项目结构

```
remotion-project/
├── package.json               # Remotion + React + 工具链
├── remotion.config.ts         # Chrome 路径 + 输出格式
├── tsconfig.json              # TS 配置(严格模式)
├── requirements.txt           # Python 依赖(requests, Pillow)
├── .env.example               # MiniMax API Key 模板
├── .gitignore                 # 忽略 node_modules/renders/public/work
│
├── src/                       # TypeScript 源码
│   ├── Root.tsx               # Composition 根
│   ├── index.ts               # registerRoot 入口
│   ├── Proof.tsx              # 主合成组件(改这里)
│   ├── geometry.tsx           # ⚠️ 风格锁定 — 调色板/字体/帧工具/SVG 坐标
│   ├── formula-panel.tsx      # ⚠️ 风格锁定 — 右侧公式面板
│   ├── caption-strip.tsx      # ⚠️ 风格锁定 — 底部字幕条
│   ├── hooks-overlay.tsx      # ⚠️ 风格锁定 — 片头/片尾遮罩
│   └── top-bar.tsx            # ⚠️ 风格锁定 — 顶部信息条
│
├── scripts/                   # 辅助脚本
│   └── generate_tts.py        # MiniMax TTS + 字幕时间轴
│
├── public/                    # 静态资产(运行时填充)
│   └── assets/
│       ├── audio/             # TTS 输出 voice.mp3
│       └── article-images/    # 抓的公众号原文图
│
├── work/                      # 中间产物
│   ├── source/                # 稿子 + 抓回的 markdown
│   ├── audio/generated/       # TTS 分段 mp3
│   └── captions/              # captions_aligned.json + captions.srt
│
└── renders/                   # 渲染输出
    ├── preview-low.mp4        # 0.5x 预览版
    └── final-1080p.mp4        # 1.0x 1080p 成片
```

---

## npm 脚本

| 命令 | 作用 |
|---|---|
| `npm run studio` | 启动 Remotion Studio 实时预览 |
| `npm run typecheck` | `tsc --noEmit` 类型检查 |
| `npm run render:preview` | 渲 0.5x 预览版(`renders/preview-low.mp4`) |
| `npm run render` | 渲 1.0x 1080p 成片(`renders/final-1080p.mp4`) |

---

## 依赖说明

### Node.js 依赖

| 包 | 版本 | 用途 |
|---|---|---|
| `remotion` | 4.0.484 | Remotion 核心 |
| `@remotion/media` | 4.0.484 | `<Audio>` 推荐来源 |
| `react` | 19.1.0 | UI 框架 |
| `react-dom` | 19.1.0 | DOM 渲染 |
| `@remotion/cli` | 4.0.484 | CLI 工具 |
| `@types/node` | 24.0.10 | Node 类型 |
| `@types/react` | 19.1.8 | React 类型 |
| `@types/react-dom` | 19.1.6 | React DOM 类型 |
| `typescript` | 5.8.3 | TS 编译器 |

### Python 依赖

```
requests>=2.31.0
Pillow>=10.0.0
```

### 系统工具

- **Google Chrome** — 渲染浏览器。`remotion.config.ts` 已设默认 Windows 路径。macOS/Linux 用户需自行修改。
- **FFmpeg + ffprobe** — 音频拼接 + 时长测量。

---

## 风格锁定文件(不要改)

以下文件是**通用样式**,**不要**为单个证明修改:

- `src/geometry.tsx` — 调色板 / 字体栈 / 帧工具 / SVG 坐标变换
- `src/formula-panel.tsx` — 右侧公式面板布局
- `src/caption-strip.tsx` — 底部字幕条布局
- `src/hooks-overlay.tsx` — 片头/片尾遮罩布局
- `src/top-bar.tsx` — 顶部信息条布局

如需新组件,在新文件里加,不要改通用文件。

---

## 常见问题

### 启动 Studio 时 Chrome 找不到

修改 `remotion.config.ts`:

```ts
// Windows
Config.setBrowserExecutable('C:/Program Files/Google/Chrome/Application/chrome.exe');
// macOS
Config.setBrowserExecutable('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
// Linux
Config.setBrowserExecutable('/usr/bin/google-chrome');
```

### 跑 TTS 时报 "未找到 MiniMax API Key"

确认 `.env` 在项目根目录,且 `minimaxi=<your-key>` 格式正确(无空格包裹 key)。

### `npm run render` 报 TS 错误

跑 `npx tsc --noEmit` 看具体错误。常见是 `²`/`₁` 等 Unicode 字符未包字符串表达式。

### 多章节 SVG 透明穿透

详见 [SKILL.md "常见坑"](../SKILL.md#常见坑)。简言之:**用条件渲染 `frame >= F.xxx && frame < F.yyy` 控制 mount/unmount,不要用 opacity。**

---

## 许可证

本模板代码(MIT):可自由使用、修改、分发。
