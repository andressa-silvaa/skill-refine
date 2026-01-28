import { useMemo } from 'react';

import type { ResumeTheme } from '@/entities/resume';
import { getResumeThemePalette } from '@/entities/resume';
import { Button, PaletteChip } from '@/shared/ui';

import './ResumeColorEditor.css';

type Props = {
  theme: ResumeTheme;
  paletteId?: string;
  onChange: (updates: { themePaletteId?: string; themeAccentOverride?: string; themeSecondaryOverride?: string }) => void;
};

export function ResumeColorEditor(props: Props) {
  const { theme, paletteId, onChange } = props;
  const palette = useMemo(() => getResumeThemePalette(theme, paletteId), [theme, paletteId]);

  return (
    <div className="sr-resume-color-editor" role="region" aria-label="Editar cores do currículo">
      <div className="sr-resume-color-editor__panel">
        <div className="sr-resume-color-editor__section">
          <span className="sr-resume-color-editor__label">Paletas</span>
          <div className="sr-resume-color-editor__palette">
            {theme.palettes.map((item) => (
              <PaletteChip
                key={item.id}
                palette={item}
                selected={(paletteId ?? theme.defaultPaletteId) === item.id}
                onSelect={() =>
                  onChange({
                    themePaletteId: item.id,
                    themeAccentOverride: undefined,
                    themeSecondaryOverride: undefined,
                  })
                }
              />
            ))}
          </div>
        </div>

        <div className="sr-resume-color-editor__actions">
          <Button
            variant="secondary"
            onClick={() =>
              onChange({
                themePaletteId: theme.defaultPaletteId,
                themeAccentOverride: undefined,
                themeSecondaryOverride: undefined,
              })
            }
          >
            Resetar
          </Button>
        </div>
      </div>
    </div>
  );
}
