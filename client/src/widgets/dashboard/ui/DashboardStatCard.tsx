import { Card } from '@/shared/ui';

import './DashboardStatCard.css';

type Props = {
  icon: string;
  iconColor?: string;
  label: string;
  value: string | number;
  sub?: string;
  badge?: string;
  badgeTone?: 'success' | 'warning' | 'neutral';
};

export function DashboardStatCard({
  icon,
  iconColor,
  label,
  value,
  sub,
  badge,
  badgeTone = 'success',
}: Props) {
  return (
    <Card className="sr-dash-stat-card">
      <div className="sr-dash-stat-card__inner">
        <div
          className="sr-dash-stat-card__icon-wrap"
          style={iconColor ? { '--stat-icon-color': iconColor } as React.CSSProperties : undefined}
        >
          <i className={icon} aria-hidden />
        </div>
        <div className="sr-dash-stat-card__body">
          <span className="sr-dash-stat-card__label">{label}</span>
          <div className="sr-dash-stat-card__value-row">
            <span className="sr-dash-stat-card__value">{value}</span>
            {badge && (
              <span className={`sr-dash-stat-card__badge sr-dash-stat-card__badge--${badgeTone}`}>
                {badge}
              </span>
            )}
          </div>
          {sub && <span className="sr-dash-stat-card__sub">{sub}</span>}
        </div>
      </div>
    </Card>
  );
}
