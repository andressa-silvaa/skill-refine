import type { ResumeThemeThumbnailSpec } from '@/entities/resume';

import './ThemeThumbnail.css';

type Props = {
  spec: ResumeThemeThumbnailSpec;
};

const PAD_X = 16;
const PAD_Y = 10;
const LINE_H = 5;
const LINE_GAP = 8;
const HEADER_H = 10;

export function ThemeThumbnail({ spec }: Props) {
  return (
    <svg className="sr-theme-thumb" viewBox="0 0 160 100" role="img" aria-hidden>
      {spec.type === 'one-column' ? (
        <>
          <rect className="sr-theme-thumb__surface" x={PAD_X} y={PAD_Y} width="128" height={spec.header === 'hero' ? 14 : HEADER_H} rx="4" />
          {Array.from({ length: spec.blocks }).map((_, idx) => (
            <rect
              key={idx}
              className="sr-theme-thumb__line"
              x={PAD_X}
              y={(spec.header === 'hero' ? 30 : 26) + idx * LINE_GAP}
              width={128 - (idx % 2) * 18}
              height={LINE_H}
              rx="3"
            />
          ))}
        </>
      ) : null}

      {spec.type === 'two-column' ? (
        <>
          <rect className="sr-theme-thumb__surface" x={PAD_X} y={PAD_Y} width="128" height={HEADER_H} rx="4" />
          <rect className="sr-theme-thumb__surface" x={spec.sidebarPosition === 'left' ? PAD_X : 96} y="26" width="44" height="62" rx="6" />
          <rect className="sr-theme-thumb__surface" x={spec.sidebarPosition === 'left' ? 68 : PAD_X} y="26" width="76" height="62" rx="6" />
          {Array.from({ length: spec.mainBlocks }).map((_, idx) => (
            <rect
              key={`main-${idx}`}
              className="sr-theme-thumb__line"
              x={spec.sidebarPosition === 'left' ? 74 : 20}
              y={32 + idx * 10}
              width="60"
              height={LINE_H}
              rx="2.5"
            />
          ))}
          {Array.from({ length: spec.sidebarBlocks }).map((_, idx) => (
            <rect
              key={`side-${idx}`}
              className="sr-theme-thumb__line"
              x={spec.sidebarPosition === 'left' ? 20 : 102}
              y={32 + idx * 12}
              width="32"
              height={LINE_H}
              rx="2.5"
            />
          ))}
        </>
      ) : null}

      {spec.type === 'timeline' ? (
        <>
          <rect className="sr-theme-thumb__surface" x={PAD_X} y={PAD_Y} width="128" height={HEADER_H} rx="4" />
          <line className="sr-theme-thumb__line-strong" x1="38" y1="26" x2="38" y2="88" />
          {Array.from({ length: spec.items }).map((_, idx) => (
            <g key={idx}>
              <circle className="sr-theme-thumb__dot" cx="38" cy={30 + idx * 14} r="3" />
              <rect className="sr-theme-thumb__line" x="46" y={27 + idx * 14} width="76" height={LINE_H} rx="3" />
            </g>
          ))}
        </>
      ) : null}

      {spec.type === 'project-grid' ? (
        <>
          <rect className="sr-theme-thumb__surface" x={PAD_X} y={PAD_Y} width="128" height={HEADER_H} rx="4" />
          {Array.from({ length: spec.rows }).map((_, row) =>
            Array.from({ length: spec.columns }).map((__, col) => (
              <rect
                key={`${row}-${col}`}
                className="sr-theme-thumb__surface"
                x={PAD_X + col * 44}
                y={26 + row * 22}
                width="38"
                height="14"
                rx="4"
              />
            ))
          )}
        </>
      ) : null}

      {spec.type === 'compact' ? (
        <>
          <rect className="sr-theme-thumb__surface" x={PAD_X} y={PAD_Y} width="128" height={HEADER_H} rx="4" />
          <rect className="sr-theme-thumb__surface" x={PAD_X} y="26" width="62" height="60" rx="5" />
          <rect className="sr-theme-thumb__surface" x="90" y="26" width="48" height="60" rx="5" />
          {Array.from({ length: spec.blocks }).map((_, idx) => (
            <rect key={idx} className="sr-theme-thumb__line" x="20" y={30 + idx * 8} width="48" height={LINE_H} rx="2.5" />
          ))}
        </>
      ) : null}
    </svg>
  );
}
