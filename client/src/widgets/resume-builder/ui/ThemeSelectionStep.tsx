import { ResumeThemePicker } from '@/features/resume-theme-select';
import type { ResumeTheme, ResumeThemeId } from '@/entities/resume';
import { PaletteChip } from '@/shared/ui';

import './ThemeSelectionStep.css';

type Props = {
  theme: ResumeTheme;
  selectedId: ResumeThemeId;
  onSelect: (id: ResumeThemeId) => void;
  selectedPaletteId?: string;
  onSelectPalette: (paletteId: string) => void;
  errorMessage?: string;
  paletteErrorMessage?: string;
};

export function ThemeSelectionStep({
  theme,
  selectedId,
  onSelect,
  selectedPaletteId,
  onSelectPalette,
  errorMessage,
  paletteErrorMessage,
}: Props) {
  return (
    <div className={`sr-theme-selection${errorMessage ? ' is-invalid' : ''}`} tabIndex={errorMessage ? -1 : undefined}>
      <div className="sr-theme-selection__header">
        <h3 className="sr-theme-selection__title">Selecione um tema visual *</h3>
        <p className="sr-theme-selection__subtitle">Escolha o estilo que melhor representa sua identidade profissional</p>
      </div>

      <ResumeThemePicker selectedId={selectedId} onSelect={onSelect} />
      {errorMessage ? <p className="sr-input-error">{errorMessage}</p> : null}

      <div className={`sr-theme-selection__palettes${paletteErrorMessage ? ' is-invalid' : ''}`}>
        <div className="sr-theme-selection__palettes-header">
          <div className="sr-theme-selection__palettes-title">Selecione uma paleta *</div>
          <div className="sr-theme-selection__palettes-subtitle">A cor do currículo (visualização e PDF) seguirá esta paleta.</div>
        </div>
        <div className="sr-theme-selection__palettes-grid" role="list" aria-label="Paletas do tema">
          {theme.palettes.map((p) => (
            <PaletteChip
              key={p.id}
              palette={p}
              selected={(selectedPaletteId ?? theme.defaultPaletteId) === p.id}
              onSelect={() => onSelectPalette(p.id)}
            />
          ))}
        </div>
        {paletteErrorMessage ? <p className="sr-input-error">{paletteErrorMessage}</p> : null}
      </div>
    </div>
  );
}
