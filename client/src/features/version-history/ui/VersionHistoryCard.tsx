import { useTranslation } from 'react-i18next';

import { Badge, Card, Chip, IconButton, Tooltip } from '@/shared/ui';
import { useMediaQuery } from '@/shared/lib/hooks/useMediaQuery';

import type { VersionHistoryItem } from '../model/types';

import './VersionHistoryCard.css';

type Props = {
  item: VersionHistoryItem;
  /** Exibe badge "Atual" e destaque visual apenas para a versão mais recente da lista */
  showAsCurrent?: boolean;
  onView: (item: VersionHistoryItem) => void;
  onRestore: (item: VersionHistoryItem) => void;
};

function formatDate(iso: string, locale: string): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat(locale, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d);
}

export function VersionHistoryCard({ item, showAsCurrent = false, onView, onRestore }: Props) {
  const { t, i18n } = useTranslation();
  const isMobile = useMediaQuery('(max-width: 480px)');
  const dateStr = formatDate(item.createdAt, i18n.language);
  const visibleChanges = isMobile ? item.changes.slice(0, 3) : item.changes;
  const hiddenChangesCount = Math.max(item.changes.length - visibleChanges.length, 0);

  return (
    <Card className="sr-version-card">
      <div className="sr-version-card__top">
        <div className="sr-version-card__icon-wrap">
          <div
            className={`sr-version-card__icon${showAsCurrent ? ' is-current' : ''}`}
            aria-hidden
          >
            <i className="fa-regular fa-file-lines" aria-hidden />
          </div>
        </div>

        <div className="sr-version-card__main">
          <div className="sr-version-card__title-row">
            <h3 className="sr-version-card__title">{item.resumeTitle}</h3>
            <div className="sr-version-card__badges">
              <Badge tone={showAsCurrent ? 'success' : 'neutral'} className="sr-version-card__badge">
                {showAsCurrent ? t('versionHistory.current') : `v${item.version}`}
              </Badge>
            </div>
          </div>
          <p className="sr-version-card__date">
            <i className="fa-regular fa-calendar" aria-hidden />
            {dateStr}
          </p>
        </div>
      </div>

      <div className="sr-version-card__footer">
        <div className="sr-version-card__score-wrap">
          <span className="sr-version-card__score" aria-label={`${item.score} ${t('versionHistory.score')}`}>
            {item.score}
          </span>
          <span className="sr-version-card__score-label">{t('versionHistory.score')}</span>
        </div>
        <div className="sr-version-card__actions">
          <Tooltip content={t('versionHistory.actions.view')}>
            <IconButton
              type="button"
              aria-label={t('versionHistory.actions.view')}
              onClick={() => onView(item)}
            >
              <i className="fa-regular fa-eye" aria-hidden />
            </IconButton>
          </Tooltip>
          {!showAsCurrent && (
            <Tooltip content={t('versionHistory.actions.restore')}>
              <IconButton
                type="button"
                aria-label={t('versionHistory.actions.restore')}
                onClick={() => onRestore(item)}
              >
                <i className="fa-solid fa-rotate-left" aria-hidden />
              </IconButton>
            </Tooltip>
          )}
        </div>
      </div>

      {item.changes.length > 0 && (
        <div className="sr-version-card__changes">
          {visibleChanges.map((change, idx) => (
            <Chip key={idx} className="sr-version-card__change-chip">
              {change}
            </Chip>
          ))}
          {hiddenChangesCount > 0 ? (
            <Chip className="sr-version-card__change-chip sr-version-card__change-chip--more">+{hiddenChangesCount}</Chip>
          ) : null}
        </div>
      )}
    </Card>
  );
}
