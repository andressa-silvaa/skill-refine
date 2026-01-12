import { Input } from '@/shared/ui';
import type { ResumeData } from '@/entities/resume';

import './BasicInfoStep.css';

type Props = {
  data: Pick<ResumeData, 'targetPosition'>;
  onChange: (updates: Partial<ResumeData>) => void;
};

export function BasicInfoStep(props: Props) {
  const { data, onChange } = props;

  return (
    <div className="sr-basic-info-step">
      <div className="sr-basic-info-step__header">
        <h3 className="sr-basic-info-step__title">Informações básicas</h3>
        <p className="sr-basic-info-step__subtitle">Defina o cargo alvo para este currículo</p>
      </div>

      <div className="sr-basic-info-step__fields">
        <Input
          label="Cargo alvo"
          placeholder="Ex.: Desenvolvedor Frontend"
          value={data.targetPosition}
          onChange={(e) => onChange({ targetPosition: e.target.value })}
          hint="O cargo que você está buscando"
        />
      </div>
    </div>
  );
}
