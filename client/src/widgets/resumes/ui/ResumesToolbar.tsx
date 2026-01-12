import { IconButton } from '@/shared/ui';

import { SortSelect } from './SortSelect';
import './ResumesToolbar.css';

type ViewMode = 'grid' | 'list';

type SortKey = 'recent' | 'score' | 'name';

type Props = {
  query: string;
  onQueryChange: (v: string) => void;
  view: ViewMode;
  onViewChange: (v: ViewMode) => void;
  sort: SortKey;
  onSortChange: (v: SortKey) => void;
  onOpenFilters: () => void;
};

const SORT_OPTIONS = [
  { value: 'recent', label: 'Mais recentes' },
  { value: 'score', label: 'Melhor score' },
  { value: 'name', label: 'Nome' },
];

export function ResumesToolbar(props: Props) {
  const { query, onQueryChange, view, onViewChange, sort, onSortChange, onOpenFilters } = props;

  return (
    <div className="sr-resumes-toolbar" role="search">
      <div className="sr-resumes-toolbar__search">
        <i className="fa-solid fa-magnifying-glass" aria-hidden />
        <input
          className="sr-resumes-toolbar__input"
          value={query}
          placeholder="Buscar currículos…"
          onChange={(e) => onQueryChange(e.target.value)}
        />
      </div>

      <div className="sr-resumes-toolbar__right">
        <div className="sr-resumes-toolbar__filters-wrapper">
          <button type="button" className="sr-btn sr-btn--secondary" onClick={onOpenFilters} title="Filtrar currículos por status, tags e outros critérios">
            <i className="fa-solid fa-filter" aria-hidden />
            Filtros
          </button>
          <span className="sr-resumes-toolbar__filters-hint">Filtrar por status, tags e mais</span>
        </div>

        <SortSelect value={sort} options={SORT_OPTIONS} onChange={(v) => onSortChange(v as SortKey)} />

        <div className="sr-resumes-toolbar__toggle" aria-label="Modo de visualização">
          <IconButton aria-label="Grid" isActive={view === 'grid'} onClick={() => onViewChange('grid')}>
            <i className="fa-solid fa-grip" aria-hidden />
          </IconButton>
          <IconButton aria-label="Lista" isActive={view === 'list'} onClick={() => onViewChange('list')}>
            <i className="fa-solid fa-list" aria-hidden />
          </IconButton>
        </div>
      </div>
    </div>
  );
}
