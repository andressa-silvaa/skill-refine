import type { ScorePoint } from '../model/types';

import './DashboardScoreChart.css';

type Props = {
  data: ScorePoint[];
};

const CHART_W = 340;
const CHART_H = 140;
const PAD_X = 8;
const PAD_Y = 16;

function getPoints(data: ScorePoint[]): { x: number; y: number }[] {
  if (data.length === 0) return [];
  if (data.length === 1) {
    return [{ x: CHART_W / 2, y: CHART_H / 2 }];
  }
  const minScore = Math.min(...data.map((d) => d.score)) - 10;
  const maxScore = Math.max(...data.map((d) => d.score)) + 5;
  const range = maxScore - minScore || 1;
  const stepX = (CHART_W - PAD_X * 2) / (data.length - 1);

  return data.map((d, i) => ({
    x: PAD_X + i * stepX,
    y: PAD_Y + (1 - (d.score - minScore) / range) * (CHART_H - PAD_Y * 2),
  }));
}

function buildPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return '';
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
  const line = buildPath(points);
  const last = points[points.length - 1]!;
  const first = points[0]!;
  return `${line} L ${last.x},${CHART_H} L ${first.x},${CHART_H} Z`;
}

export function DashboardScoreChart({ data }: Props) {
  const points = getPoints(data);
  const linePath = buildPath(points);
  const areaPath = buildAreaPath(points);

  return (
    <div className="sr-dash-score-chart">
      <svg
        viewBox={`0 0 ${CHART_W} ${CHART_H}`}
        preserveAspectRatio="none"
        aria-hidden
        className="sr-dash-score-chart__svg"
      >
        <defs>
          <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--sr-accent)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--sr-accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#scoreGrad)" />
        <path
          d={linePath}
          fill="none"
          stroke="var(--sr-accent)"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {points.map((p, i) => (
          <circle
            key={i}
            cx={p.x}
            cy={p.y}
            r="3.5"
            fill="var(--sr-accent)"
            stroke="var(--sr-surface)"
            strokeWidth="2"
          />
        ))}
      </svg>
      <div className="sr-dash-score-chart__labels">
        {data.map((d) => (
          <span key={d.month} className="sr-dash-score-chart__month">
            {d.month}
          </span>
        ))}
      </div>
    </div>
  );
}
