import type { ReactNode } from 'react';

import { Card, Badge } from '@/shared/ui';

import './MetricCard.css';

type Props = {
  icon: ReactNode;
  label: string;
  value: ReactNode;
  /** Estilo do valor: default (número grande) ou text (texto menor, ex. senioridade) */
  valueVariant?: 'default' | 'text';
  /** Badge ou subtexto opcional (ex.: "Excelente", "Estimativa") */
  badge?: string;
  /** Tone do badge: success (verde), neutral (azul/neutro), warning (amarelo) */
  badgeTone?: 'success' | 'neutral' | 'warning';
};

export function MetricCard(props: Props) {
  const { icon, label, value, valueVariant = 'default', badge, badgeTone = 'neutral' } = props;

  return (
    <Card className="sr-metric-card">
      <div className="sr-metric-card__icon" aria-hidden>
        {icon}
      </div>
      <span className="sr-metric-card__label">{label}</span>
      <span className={`sr-metric-card__value${valueVariant === 'text' ? ' sr-metric-card__value--text' : ''}`}>
        {value}
      </span>
      {badge ? (
        <Badge tone={badgeTone} className="sr-metric-card__badge">
          {badge}
        </Badge>
      ) : null}
    </Card>
  );
}
