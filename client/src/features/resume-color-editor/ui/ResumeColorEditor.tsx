import { useTranslation } from 'react-i18next';

import type { ResumeTheme } from '@/entities/resume';
import { Button, PaletteChip } from '@/shared/ui';

import './ResumeColorEditor.css';

type Props = {
  theme: ResumeTheme;
  paletteId?: string;
  onChange: (updates: { themePaletteId?: string; themeAccentOverride?: string; themeSecondaryOverride?: string }) => void;
};

export function ResumeColorEditor(props: Props) {
  const { t } = useTranslation();
  const { theme, paletteId, onChange } = props;

  return (
    <div className="sr-resume-color-editor" role="region" aria-label={t('resume.colorEditorAria')}>
      <div className="sr-resume-color-editor__panel">
        <div className="sr-resume-color-editor__section">
          <span className="sr-resume-color-editor__label">{t('resume.colorEditorPalettes')}</span>
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
            {t('resume.colorEditorReset')}
          </Button>
        </div>
      </div>
    </div>
  );
}
