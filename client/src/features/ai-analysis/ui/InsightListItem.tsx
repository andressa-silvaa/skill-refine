import { useTranslation } from 'react-i18next';

import { Card, Button, Badge } from '@/shared/ui';

import type { ImprovementInsightItem, ImprovementPriority, InsightItem } from '../model/types';

import './InsightListItem.css';

function priorityToTone(priority: ImprovementPriority): 'success' | 'neutral' | 'warning' {
  if (priority === 'high') return 'warning';
  if (priority === 'medium') return 'neutral';
  return 'success';
}

type Props =
  | {
      variant: 'positive';
      /** Canonical: key + params for i18n t(key, params) */
      insight: InsightItem;
    }
  | {
      variant: 'improvement';
      insight: ImprovementInsightItem;
      onSeeExample?: (insight: ImprovementInsightItem) => void;
      onApply?: (insight: ImprovementInsightItem) => void;
      applying?: boolean;
    };

export function InsightListItem(props: Props) {
  const { t } = useTranslation();

  if (props.variant === 'positive') {
    const { insight } = props;
    const text = insight.params && Object.keys(insight.params).length > 0
      ? t(insight.key, insight.params)
      : t(insight.key);
    return (
      <Card className="sr-insight-item sr-insight-item--positive">
        <span className="sr-insight-item__icon sr-insight-item__icon--success" aria-hidden>
          <i className="fa-solid fa-circle-check" />
        </span>
        <p className="sr-insight-item__text">{text}</p>
      </Card>
    );
  }

  const { insight, onSeeExample, onApply, applying = false } = props;
  const text = insight.params && Object.keys(insight.params).length > 0
    ? t(insight.key, insight.params)
    : t(insight.key);
  const priority = insight.priority;
  const priorityLabel =
    priority === 'high'
      ? t('analysis.priorityHigh')
      : priority === 'medium'
        ? t('analysis.priorityMedium')
        : priority === 'low'
          ? t('analysis.priorityLow')
          : null;

  return (
    <Card className="sr-insight-item sr-insight-item--improvement">
      <span className="sr-insight-item__icon sr-insight-item__icon--warning" aria-hidden>
        <i className="fa-solid fa-triangle-exclamation" />
      </span>
      <div className="sr-insight-item__body">
        <p className="sr-insight-item__text">{text}</p>
        {priorityLabel ? (
          <Badge tone={priorityToTone(priority!)} className="sr-insight-item__priority">
            {priorityLabel}
          </Badge>
        ) : null}
        <div className="sr-insight-item__actions">
          {onSeeExample ? (
            <Button
              variant="secondary"
              type="button"
              onClick={() => onSeeExample(insight)}
              className="sr-insight-item__btn"
              disabled={applying}
            >
              {t('analysis.seeExample')}
            </Button>
          ) : null}
          {onApply ? (
            <Button
              variant="ghost"
              type="button"
              onClick={() => onApply(insight)}
              className="sr-insight-item__btn"
              disabled={applying}
            >
              {applying ? t('analysis.applying') : t('analysis.applyToResume')}
            </Button>
          ) : null}
        </div>
      </div>
    </Card>
  );
}
