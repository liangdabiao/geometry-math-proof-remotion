/**
 * 顶部信息条 (h=90):
 *   左: 系列名 · 子标题(灰色)
 *   右: 当前章节名(白色) · 章节公式/要点(黄色)
 *
 * 用法:
 *   1. 在 Proof.tsx 准备 TOPBAR: { series, subtitle, chapter, formula }
 *   2. <TopBar frame={frame} data={TOPBAR} activeFrom={F.<章节>} activeTo={F.<下章>}/>
 *
 * activeFrom/activeTo 控制当前章节高亮的起止帧;不在区间时显示默认 series 信息。
 */
import React from 'react';
import {C, FONT_SANS, FONT_MATH, fadeIn} from './geometry';

export type TopBarData = {
  series: string;          // 系列名,例如 "Pythagorean Proofs"
  subtitle: string;        // 副标题,例如 "EP 01 · 几何证明"
  chapter: string;         // 当前章节名,例如 "准备: 直角三角形"
  formula?: string;        // 当前章节重点公式,黄色大字
};

export const TopBar: React.FC<{
  frame: number;
  data: TopBarData;
  activeFrom?: number;     // 当前章节起始帧
  activeTo?: number;       // 当前章节结束帧(下章起始)
}> = ({frame: f, data, activeFrom = 0, activeTo = Infinity}) => {
  const active = f >= activeFrom && f < activeTo;
  const op = fadeIn(f, activeFrom, 18, 1);
  return (
    <div style={{
      position: 'absolute', top: 0, left: 0, right: 0, height: 90,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 60px',
      background: 'linear-gradient(180deg, rgba(13,13,18,0.92), rgba(13,13,18,0.0))',
      opacity: op,
    }}>
      {/* 左: 系列名 + 副标题 */}
      <div style={{display: 'flex', flexDirection: 'column', gap: 4}}>
        <span style={{
          fontFamily: FONT_SANS, fontSize: 22, color: C.text,
          letterSpacing: 2, textTransform: 'uppercase',
        }}>
          {data.series}
        </span>
        <span style={{
          fontFamily: FONT_SANS, fontSize: 16, color: C.textDim,
          letterSpacing: 1,
        }}>
          {data.subtitle}
        </span>
      </div>

      {/* 右: 章节名 + 重点公式 */}
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4}}>
        <span style={{
          fontFamily: FONT_SANS, fontSize: 20, color: active ? C.text : C.textDim,
          letterSpacing: 1,
        }}>
          {data.chapter}
        </span>
        {data.formula && (
          <span style={{
            fontFamily: FONT_MATH, fontSize: 28, color: C.yellow,
            letterSpacing: 1,
          }}>
            {data.formula}
          </span>
        )}
      </div>
    </div>
  );
};
