import { useTranslation } from 'react-i18next';

import { Badge, Button, Chip, Modal } from '@/shared/ui';

import type { VersionHistoryItem } from '../model/types';

import './VersionViewModal.css';

type Props = {
  open: boolean;
  item: VersionHistoryItem | null;
  onClose: () => void;
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

function getScoreTone(score: number): 'good' | 'mid' | 'low' {
  if (score >= 75) return 'good';
  if (score >= 50) return 'mid';
  return 'low';
}

export function VersionViewModal({ open, item, onClose }: Props) {
  const { t, i18n } = useTranslation();

  if (!item) return null;

  const dateStr = formatDate(item.createdAt, i18n.language);
  const subtitle = `v${item.version} · ${dateStr}`;
  const scoreTone = getScoreTone(item.score);

  return (
    <Modal
      open={open}
      title={item.resumeTitle}
      subtitle={subtitle}
      width={500}
      onClose={onClose}
    >
      <div className="sr-version-view">

        {/* ── Meta row: badges ── */}
        <div className="sr-version-view__meta">
          <Badge tone="neutral">v{item.version}</Badge>
          {item.isCurrent && (
            <Badge tone="success">{t('versionHistory.current')}</Badge>
          )}
        </div>

        {/* ── Score block ── */}
        <div className="sr-version-view__score-block">
          <div className={`sr-version-view__score-circle sr-version-view__score-circle--${scoreTone}`}>
            <span className="sr-version-view__score-value">{item.score}</span>
          </div>
          <div className="sr-version-view__score-info">
            <span className="sr-version-view__score-label">{t('versionHistory.score')}</span>
            <span className="sr-version-view__score-sub">
              {scoreTone === 'good'
                ? t('versionHistory.viewModal.scoreGood')
                : scoreTone === 'mid'
                  ? t('versionHistory.viewModal.scoreMid')
                  : t('versionHistory.viewModal.scoreLow')}
            </span>
          </div>
        </div>

        {/* ── Divider ── */}
        <div className="sr-version-view__divider" role="separator" />

        {/* ── Changes ── */}
        <div className="sr-version-view__changes">
          <h4 className="sr-version-view__changes-title">
            <i className="fa-solid fa-list-check" aria-hidden />
            {t('versionHistory.viewModalChanges')}
          </h4>
          {item.changes.length > 0 ? (
            <div className="sr-version-view__chips">
              {item.changes.map((change, idx) => (
                <Chip key={idx}>{change}</Chip>
              ))}
            </div>
          ) : (
            <p className="sr-version-view__no-changes">
              {t('versionHistory.viewModalNoChanges')}
            </p>
          )}
        </div>

        {/* ── Actions ── */}
        <div className="sr-version-view__actions">
          <Button variant="secondary" onClick={onClose}>
            {t('versionHistory.viewModalClose')}
          </Button>
        </div>

      </div>
    </Modal>
  );
}
