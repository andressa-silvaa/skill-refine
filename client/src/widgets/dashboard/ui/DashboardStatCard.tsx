import { useIsTruncated, useIsVerticallyClamped } from '@/shared/lib/hooks/useIsTruncated';
import { useMediaQuery } from '@/shared/lib/hooks/useMediaQuery';
import { Card, Tooltip } from '@/shared/ui';

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
  /** Native title on touch/coarse pointers where hover tooltip does not run. */
  const canHover = useMediaQuery('(hover: hover)');
  const valueStr = String(value);
  const { ref: labelRef, isClamped: labelClamped } = useIsVerticallyClamped<HTMLSpanElement>(label);
  const { ref: valueRef, isTruncated: valueTruncated } = useIsTruncated<HTMLSpanElement>(valueStr);
  const { ref: subRef, isClamped: subClamped } = useIsVerticallyClamped<HTMLSpanElement>(sub ?? '');

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
          <Tooltip content={label} show={labelClamped} align="top" className="sr-dash-stat-card__label-tooltip">
            <span
              ref={labelRef}
              className="sr-dash-stat-card__label"
              title={labelClamped && !canHover ? label : undefined}
            >
              {label}
            </span>
          </Tooltip>
          <div className="sr-dash-stat-card__value-row">
            <Tooltip content={valueStr} show={valueTruncated} align="top" className="sr-dash-stat-card__value-tooltip">
              <span
                ref={valueRef}
                className="sr-dash-stat-card__value"
                title={valueTruncated && !canHover ? valueStr : undefined}
              >
                {value}
              </span>
            </Tooltip>
            {badge && (
              <span className={`sr-dash-stat-card__badge sr-dash-stat-card__badge--${badgeTone}`}>
                {badge}
              </span>
            )}
          </div>
          {sub && (
            <Tooltip content={sub} show={subClamped} align="top" className="sr-dash-stat-card__sub-tooltip">
              <span
                ref={subRef}
                className="sr-dash-stat-card__sub"
                title={subClamped && !canHover ? sub : undefined}
              >
                {sub}
              </span>
            </Tooltip>
          )}
        </div>
      </div>
    </Card>
  );
}
