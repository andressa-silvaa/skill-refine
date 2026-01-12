import { Textarea } from '@/shared/ui';

import './SummaryStep.css';

type Props = {
  summary: string;
  onChange: (summary: string) => void;
};

export function SummaryStep(props: Props) {
  const { summary, onChange } = props;

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
        showCount
        maxLength={500}
        hint="Dica: Use palavras-chave relevantes para ATS e seja específico sobre suas conquistas."
      />

      <div className="sr-summary-step__actions">
        <button type="button" className="sr-summary-step__ai-button" onClick={() => alert('Funcionalidade de IA em breve')}>
          <i className="fa-solid fa-sparkles" aria-hidden />
          Aprimorar com IA
        </button>
      </div>
    </div>
  );
}
