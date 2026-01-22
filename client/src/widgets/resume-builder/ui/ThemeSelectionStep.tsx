import { ResumeThemePicker } from '@/features/resume-theme-select';
import type { ResumeThemeId } from '@/entities/resume';

import './ThemeSelectionStep.css';

type Props = {
  selectedId: ResumeThemeId;
  onSelect: (id: ResumeThemeId) => void;
};

export function ThemeSelectionStep({ selectedId, onSelect }: Props) {
  return (
    <div className="sr-theme-selection">
      <div className="sr-theme-selection__header">
        <h3 className="sr-theme-selection__title">Selecione um tema visual</h3>
        <p className="sr-theme-selection__subtitle">Escolha o estilo que melhor representa sua identidade profissional</p>
      </div>

      <ResumeThemePicker selectedId={selectedId} onSelect={onSelect} />
    </div>
  );
}
