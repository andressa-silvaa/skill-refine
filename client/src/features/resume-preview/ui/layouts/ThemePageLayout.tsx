import type { ThemeBlock, ThemeLayoutData } from '../types';

type ThemePageProps = {
  layout: ThemeLayoutData;
  mainBlocks: ThemeBlock[];
  sidebarBlocks?: ThemeBlock[];
};

export function ThemePageLayout({ layout, mainBlocks, sidebarBlocks }: ThemePageProps) {
  if (layout.type === 'two-column') {
    const headerBlocks =
      layout.headerPlacement === 'full' ? mainBlocks.filter((block) => block.kind === 'header') : [];
    const mainContent =
      layout.headerPlacement === 'full' ? mainBlocks.filter((block) => block.kind !== 'header') : mainBlocks;

    return (
      <div className={`sr-resume-theme__layout sr-resume-theme__layout--${layout.variant}`}>
        {headerBlocks.length ? (
          <div className="sr-resume-theme__header-blocks">
            {headerBlocks.map((block) => (
              <div key={block.key} className="sr-resume-page__block" data-breakable={block.breakable ? 'true' : 'false'}>
                {block.node}
              </div>
            ))}
          </div>
        ) : null}
        <div className="sr-resume-theme__columns">
          <div className="sr-resume-theme__column sr-resume-theme__main">
            {mainContent.map((block) => (
              <div key={block.key} className="sr-resume-page__block" data-breakable={block.breakable ? 'true' : 'false'}>
                {block.node}
              </div>
            ))}
          </div>
          <aside className="sr-resume-theme__column sr-resume-theme__sidebar">
            {(sidebarBlocks ?? []).map((block) => (
              <div key={block.key} className="sr-resume-page__block" data-breakable={block.breakable ? 'true' : 'false'}>
                {block.node}
              </div>
            ))}
          </aside>
        </div>
      </div>
    );
  }

  return (
    <div className={`sr-resume-theme__layout sr-resume-theme__layout--${layout.variant ?? 'single'}`}>
      {mainBlocks.map((block) => (
        <div key={block.key} className="sr-resume-page__block" data-breakable={block.breakable ? 'true' : 'false'}>
          {block.node}
        </div>
      ))}
    </div>
  );
}
