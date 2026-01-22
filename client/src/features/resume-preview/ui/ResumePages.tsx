import { useMemo } from 'react';

import type { ThemeLayoutData, ThemeBlock } from './ThemeRenderer';
import { ThemePageLayout } from './ThemeRenderer';
import { usePaginatedBlocks } from '../model/usePaginatedBlocks';

import './ResumePages.css';

const A4_PAGE = {
  width: 794,
  height: 1123,
};

const DEFAULT_PADDING = 48;

const parsePx = (value?: string, fallback = 0) => {
  if (!value) return fallback;
  const parsed = parseFloat(value.replace('px', ''));
  return Number.isNaN(parsed) ? fallback : parsed;
};

type Props = {
  layout: ThemeLayoutData;
  sectionGap: string | undefined;
};

export function ResumePages({ layout, sectionGap }: Props) {
  const gap = parsePx(sectionGap, 16);
  const contentHeight = A4_PAGE.height - DEFAULT_PADDING * 2;
  // Root cause: o preview ficava em uma unica pagina com overflow. Aqui paginamos por altura A4.

  const { pages: mainPages, register: registerMain } = usePaginatedBlocks(
    layout.type === 'single' ? layout.blocks : layout.main,
    { pageHeight: contentHeight, gap }
  );

  const { pages: sidebarPages, register: registerSidebar } = usePaginatedBlocks(
    layout.type === 'single' ? [] : layout.sidebar,
    { pageHeight: contentHeight, gap }
  );

  const pageCount = Math.max(mainPages.length, sidebarPages.length);

  const pages = useMemo(
    () =>
      Array.from({ length: pageCount }).map((_, idx) => ({
        main: mainPages[idx] ?? [],
        sidebar: sidebarPages[idx] ?? [],
      })),
    [mainPages, sidebarPages, pageCount]
  );

  const mainHeaderBlocks = layout.type === 'two-column' && layout.headerPlacement === 'full'
    ? layout.main.map((block, index) => ({ block, index })).filter(({ block }) => block.kind === 'header')
    : [];
  const mainContentBlocks = layout.type === 'two-column' && layout.headerPlacement === 'full'
    ? layout.main.map((block, index) => ({ block, index })).filter(({ block }) => block.kind !== 'header')
    : layout.type === 'two-column'
    ? layout.main.map((block, index) => ({ block, index }))
    : [];

  return (
    <div className="sr-resume-pages" style={{ '--resume-page-width': `${A4_PAGE.width}px`, '--resume-page-height': `${A4_PAGE.height}px` } as React.CSSProperties}>
      {pages.map((page, index) => (
        <div key={`page-${index}`} className="sr-resume-page" role="article" aria-label={`Página ${index + 1}`}>
          <div className="sr-resume-page__content">
            <ThemePageLayout layout={layout} mainBlocks={page.main} sidebarBlocks={layout.type === 'single' ? undefined : page.sidebar} />
          </div>
        </div>
      ))}

      <div className="sr-resume-pages__measure" aria-hidden>
        {layout.type === 'single' ? (
          <div className="sr-resume-page__content sr-resume-page__content--measure">
            <div className={`sr-resume-theme__layout sr-resume-theme__layout--${layout.variant ?? 'single'}`}>
              {layout.blocks.map((block, index) => (
                <div key={block.key} ref={registerMain(index)} className="sr-resume-page__block">
                  {block.node}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className={`sr-resume-page__content sr-resume-page__content--measure sr-resume-page__content--${layout.variant}`}>
            <div className={`sr-resume-theme__layout sr-resume-theme__layout--${layout.variant}`}>
              {layout.headerPlacement === 'full' && mainHeaderBlocks.length ? (
                <div className="sr-resume-theme__header-blocks">
                  {mainHeaderBlocks.map(({ block, index }) => (
                    <div key={block.key} ref={registerMain(index)} className="sr-resume-page__block">
                      {block.node}
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="sr-resume-theme__columns">
                <div className="sr-resume-theme__column sr-resume-theme__main">
                  {mainContentBlocks.map(({ block, index }) => (
                    <div key={block.key} ref={registerMain(index)} className="sr-resume-page__block">
                      {block.node}
                    </div>
                  ))}
                </div>
                <aside className="sr-resume-theme__column sr-resume-theme__sidebar">
                  {layout.sidebar.map((block, index) => (
                    <div key={block.key} ref={registerSidebar(index)} className="sr-resume-page__block">
                      {block.node}
                    </div>
                  ))}
                </aside>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
