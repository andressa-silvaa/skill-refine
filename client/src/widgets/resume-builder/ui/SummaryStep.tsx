import { useState } from 'react';

import { Button, Textarea } from '@/shared/ui';
import { resumeApi } from '@/features/resume/api/resumeApi';
import { notify } from '@/shared/lib/notify';
import { getApiErrorMessage } from '@/shared/api';

import './SummaryStep.css';

type Props = {
  summary: string;
  onChange: (summary: string) => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
};

export function SummaryStep(props: Props) {
  const { summary, onChange, getError, shouldShowError, onFieldTouched } = props;
  const summaryError = shouldShowError('summary') ? getError('summary') : undefined;
  const [isImproving, setIsImproving] = useState(false);

  return (
    <div className="sr-summary-step">
      <div className="sr-summary-step__header">
        <h3 className="sr-summary-step__title">Resumo profissional</h3>
        <p className="sr-summary-step__subtitle">Um resumo conciso que destaque seus principais pontos fortes</p>
      </div>

      <Textarea
        label="Resumo"
        placeholder="Ex.: Desenvolvedor Full Stack com 5+ anos de experiência em React, Node.js e TypeScript. Especialista em arquitetura de software escalável e liderança de equipes técnicas."
        value={summary}
        onChange={(e) => onChange(e.target.value)}
        onBlur={() => onFieldTouched('summary')}
        showCount
        maxLength={500}
        hint="Dica: Use palavras-chave relevantes para ATS e seja específico sobre suas conquistas."
        error={summaryError}
      />

      <div className="sr-summary-step__actions">
        <Button
          variant="primary"
          className="sr-summary-step__ai-button"
          disabled={isImproving}
          onClick={async () => {
            if (!summary.trim()) {
              notify.error('Digite um resumo antes de aprimorar com IA.');
              return;
            }
            setIsImproving(true);
            try {
              const result = await resumeApi.rewriteSummaryWithAI(summary);
              onChange(result.suggestedText);
            } catch (err) {
              notify.error(getApiErrorMessage(err, 'Não foi possível aprimorar o resumo agora. Tente novamente em instantes.'));
            } finally {
              setIsImproving(false);
            }
          }}
        >
          {isImproving ? <i className="fa-solid fa-circle-notch fa-spin" aria-hidden /> : <i className="fa-solid fa-wand-magic-sparkles" aria-hidden />}
          {isImproving ? 'Aprimorando...' : 'Aprimorar com IA'}
        </Button>
      </div>
    </div>
  );
}
