import { useId } from 'react';

import type { ScorePoint } from '../model/types';

import './DashboardScoreChart.css';

type Props = {
  data: ScorePoint[];
};

const CHART_W = 340;
const CHART_H = 140;
const PAD_X = 12;
const PAD_Y = 14;

/** Domínio vertical com faixa mínima para 1–2 pontos ou scores iguais. */
function scoreYDomain(scores: number[]): { min: number; max: number } {
  if (scores.length === 0) return { min: 0, max: 100 };
  const rawMin = Math.min(...scores);
  const rawMax = Math.max(...scores);
  const pad = 10;
  if (rawMin === rawMax) {
    const c = rawMin;
    return {
      min: Math.max(0, c - 14),
      max: Math.min(100, c + 14),
    };
  }
  return {
    min: Math.max(0, rawMin - pad),
    max: Math.min(100, rawMax + pad),
  };
}

function getPoints(data: ScorePoint[]): { x: number; y: number }[] {
  if (data.length === 0) return [];

  const scores = data.map((d) => d.score);
  const { min: yMin, max: yMax } = scoreYDomain(scores);
  const yRange = Math.max(yMax - yMin, 1);
  const innerW = CHART_W - PAD_X * 2;
  const innerH = CHART_H - PAD_Y * 2;

  const yFor = (score: number) => PAD_Y + (1 - (score - yMin) / yRange) * innerH;

  if (data.length === 1) {
    return [{ x: CHART_W / 2, y: yFor(scores[0]!) }];
  }

  const n = data.length;
  return data.map((d, i) => ({
    x: PAD_X + (innerW * i) / (n - 1),
    y: yFor(d.score),
  }));
}

/** Curva suave só com vários pontos; poucos pontos = linhas retas (mais legível). */
function buildPath(points: { x: number; y: number }[]): string {
  if (points.length < 2) return '';
  if (points.length <= 3) {
    return points.map((p, i) => (i === 0 ? `M ${p.x},${p.y}` : `L ${p.x},${p.y}`)).join(' ');
  }
  return points
    .map((p, i) => {
      if (i === 0) return `M ${p.x},${p.y}`;
      const prev = points[i - 1]!;
      const cpX = (prev.x + p.x) / 2;
      return `C ${cpX},${prev.y} ${cpX},${p.y} ${p.x},${p.y}`;
    })
    .join(' ');
}

function buildAreaPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return '';
  if (points.length === 1) {
    const p = points[0]!;
    const half = 28;
    return `M ${p.x - half},${CHART_H} L ${p.x - half},${p.y} L ${p.x + half},${p.y} L ${p.x + half},${CHART_H} Z`;
  }
  const line = buildPath(points);
  const last = points[points.length - 1]!;
  const first = points[0]!;
  return `${line} L ${last.x},${CHART_H} L ${first.x},${CHART_H} Z`;
}

/** Mesmo mês em mais de um ponto: rótulos distintos para não colidir em React e no layout. */
function monthLabels(data: ScorePoint[]): string[] {
  const countByMonth = new Map<string, number>();
  data.forEach((d) => countByMonth.set(d.month, (countByMonth.get(d.month) ?? 0) + 1));
  const seen = new Map<string, number>();
  return data.map((d) => {
    const total = countByMonth.get(d.month) ?? 1;
    if (total <= 1) return d.month;
    const n = (seen.get(d.month) ?? 0) + 1;
    seen.set(d.month, n);
    return `${d.month} (${n})`;
  });
}

export function DashboardScoreChart({ data }: Props) {
  const gradId = `scoreGrad-${useId().replace(/:/g, '')}`;
  const points = getPoints(data);
  const linePath = buildPath(points);
  const areaPath = buildAreaPath(points);
  const labels = monthLabels(data);
  const scores = data.map((d) => d.score);
  const { min: yMin, max: yMax } = scoreYDomain(scores);
  const yMid = Math.round((yMin + yMax) / 2);

  return (
    <div className="sr-dash-score-chart">
      <div className="sr-dash-score-chart__plot-row">
        <div className="sr-dash-score-chart__y-axis" aria-hidden>
          <span>{Math.round(yMax)}</span>
          <span>{yMid}</span>
          <span>{Math.round(yMin)}</span>
        </div>
        <svg
          viewBox={`0 0 ${CHART_W} ${CHART_H}`}
          preserveAspectRatio="xMidYMid meet"
          aria-hidden
          className="sr-dash-score-chart__svg"
        >
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--sr-accent)" stopOpacity="0.22" />
              <stop offset="100%" stopColor="var(--sr-accent)" stopOpacity="0" />
            </linearGradient>
          </defs>
          {areaPath ? <path d={areaPath} fill={`url(#${gradId})`} /> : null}
          {linePath ? (
            <path
              d={linePath}
              fill="none"
              stroke="var(--sr-accent)"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ) : null}
          {points.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={data.length === 1 ? 4.5 : 3.75}
              fill="var(--sr-accent)"
              stroke="var(--sr-surface)"
              strokeWidth="2"
            />
          ))}
        </svg>
      </div>
      <div
        className="sr-dash-score-chart__labels"
        style={{ gridTemplateColumns: `repeat(${data.length}, minmax(0, 1fr))` }}
      >
        {labels.map((label, i) => (
          <span key={`${i}-${label}`} className="sr-dash-score-chart__month" title={`${data[i]?.score ?? ''}/100`}>
            <span className="sr-dash-score-chart__month-label">{label}</span>
            <span className="sr-dash-score-chart__month-score">{data[i]?.score ?? '—'}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
