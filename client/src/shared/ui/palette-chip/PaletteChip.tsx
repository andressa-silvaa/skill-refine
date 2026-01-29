import { useTranslation } from 'react-i18next';

import './PaletteChip.css';

type Palette = {
  id: string;
  name: string;
  nameKey?: string;
  accent: string;
};

type Props = {
  palette: Palette;
  selected: boolean;
  onSelect: () => void;
};

export function PaletteChip({ palette, selected, onSelect }: Props) {
  const { t } = useTranslation();
  const displayName = palette.nameKey ? t(palette.nameKey) : palette.name;

  return (
    <button
      type="button"
      className={`sr-palette-chip${selected ? ' is-selected' : ''}`}
      onClick={onSelect}
      aria-pressed={selected}
    >
      <span className="sr-palette-chip__swatch" style={{ background: palette.accent }} aria-hidden />
      <span className="sr-palette-chip__label">{displayName}</span>
      {selected ? <i className="fa-solid fa-check" aria-hidden /> : null}
    </button>
  );
}
