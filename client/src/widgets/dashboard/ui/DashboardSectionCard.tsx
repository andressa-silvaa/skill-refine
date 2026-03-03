import type { ReactNode } from 'react';

import { Card } from '@/shared/ui';

import './DashboardSectionCard.css';

type Props = {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function DashboardSectionCard({ title, action, children, className = '' }: Props) {
  return (
    <Card className={`sr-dash-section-card${className ? ` ${className}` : ''}`}>
      <div className="sr-dash-section-card__header">
        <h2 className="sr-dash-section-card__title">{title}</h2>
        {action && <div className="sr-dash-section-card__action">{action}</div>}
      </div>
      <div className="sr-dash-section-card__body">{children}</div>
    </Card>
  );
}
