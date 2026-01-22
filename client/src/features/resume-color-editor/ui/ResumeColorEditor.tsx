import { useMemo, useState } from 'react';

import type { ResumeTheme } from '@/entities/resume';
import { getResumeThemePalette } from '@/entities/resume';
import { Button, ColorPicker, PaletteChip } from '@/shared/ui';

import './ResumeColorEditor.css';

type Props = {
  theme: ResumeTheme;
  paletteId?: string;
  accentOverride?: string;
  secondaryOverride?: string;
  onChange: (updates: { themePaletteId?: string; themeAccentOverride?: string; themeSecondaryOverride?: string }) => void;
};

export function ResumeColorEditor(props: Props) {
  const { theme, paletteId, accentOverride, secondaryOverride, onChange } = props;
  const [error, setError] = useState<string | null>(null);
  const palette = useMemo(() => getResumeThemePalette(theme, paletteId), [theme, paletteId]);

  const background = theme.styleTokens.paperBg ?? '#ffffff';
  // Como adicionar novos controles: inclua na UI + valide contraste antes de aplicar.

  const applyAccent = (value: string) => {
    if (!isContrastOk(value, background)) {
      setError('Cor com contraste baixo. Escolha outra.');
      return;
    }
    setError(null);
    onChange({ themeAccentOverride: value });
  };

  const applySecondary = (value: string) => {
    if (!value) {
      onChange({ themeSecondaryOverride: undefined });
      return;
    }
    if (!isContrastOk(value, background)) {
      setError('Cor secundária com contraste baixo.');
      return;
    }
    setError(null);
    onChange({ themeSecondaryOverride: value });
  };

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
                onSelect={() => onChange({ themePaletteId: item.id, themeAccentOverride: undefined, themeSecondaryOverride: undefined })}
              />
            ))}
          </div>
        </div>

        <div className="sr-resume-color-editor__section">
          <span className="sr-resume-color-editor__label">Cor principal</span>
          <ColorPicker value={accentOverride ?? palette.accent} onChange={applyAccent} ariaLabel="Cor principal" />
        </div>

        <div className="sr-resume-color-editor__section">
          <span className="sr-resume-color-editor__label">Cor secundária (opcional)</span>
          <ColorPicker value={secondaryOverride ?? palette.accent} onChange={applySecondary} ariaLabel="Cor secundária" />
        </div>

        <div className="sr-resume-color-editor__actions">
          <Button
            variant="secondary"
            onClick={() => onChange({ themePaletteId: theme.defaultPaletteId, themeAccentOverride: undefined, themeSecondaryOverride: undefined })}
          >
            Resetar
          </Button>
        </div>

        {error ? <p className="sr-resume-color-editor__error">{error}</p> : null}
      </div>
    </div>
  );
}

function isContrastOk(foreground: string, background: string) {
  const ratio = getContrastRatio(foreground, background);
  return ratio >= 4.5;
}

function getContrastRatio(fg: string, bg: string) {
  const [fr, fg2, fb] = hexToRgb(fg);
  const [br, bg2, bb] = hexToRgb(bg);
  const l1 = luminance(fr, fg2, fb);
  const l2 = luminance(br, bg2, bb);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function luminance(r: number, g: number, b: number) {
  const toLinear = (value: number) => {
    const v = value / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

function hexToRgb(hex: string): [number, number, number] {
  const normalized = hex.replace('#', '');
  if (normalized.length !== 6) return [0, 0, 0];
  const r = parseInt(normalized.slice(0, 2), 16);
  const g = parseInt(normalized.slice(2, 4), 16);
  const b = parseInt(normalized.slice(4, 6), 16);
  return [r, g, b];
}
