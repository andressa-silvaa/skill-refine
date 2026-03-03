import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { AppShell } from '@/widgets/app-shell';
import {
  useVersionHistory,
  VersionHistoryFilters,
  VersionHistoryList,
  VersionHistoryEmptyState,
  versionHistoryApi,
} from '@/features/version-history';
import { useResumes } from '@/features/resume';
import { Button, Modal } from '@/shared/ui';
import { notify } from '@/shared/lib/notify';

import type { VersionHistoryItem } from '@/features/version-history';

import './VersionHistoryPage.css';

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

export function VersionHistoryPage() {
  const { t, i18n } = useTranslation();
  const resumes = useResumes();
  const {
    versions,
    resumeOptions,
    activeFilterId,
    setFilter,
    allFilterId,
    loading,
    error,
    refetch,
  } = useVersionHistory();

  const [viewModalItem, setViewModalItem] = useState<VersionHistoryItem | null>(null);
  const [restoreModalItem, setRestoreModalItem] = useState<VersionHistoryItem | null>(null);

  const handleView = (item: VersionHistoryItem) => {
    setViewModalItem(item);
  };

  const handleRestore = (item: VersionHistoryItem) => {
    setRestoreModalItem(item);
  };

  const [restoring, setRestoring] = useState(false);
  const confirmRestore = async () => {
    if (!restoreModalItem) return;
    setRestoring(true);
    try {
      await versionHistoryApi.restore(restoreModalItem.resumeId, restoreModalItem.id);
      notify.success(t('versionHistory.restoreSuccess'));
      setRestoreModalItem(null);
      refetch();
      void resumes.reload();
    } catch {
      notify.error(t('versionHistory.restoreFailed'));
    } finally {
      setRestoring(false);
    }
  };

  const showEmpty = !loading && versions.length === 0;
  const showError = Boolean(error);

  return (
    <AppShell>
      <main className="sr-version-history" aria-label={t('versionHistory.mainAria')}>
        <div className="sr-version-history__container">
          <header className="sr-version-history__header">
            <div>
              <h1 className="sr-version-history__h1">{t('versionHistory.title')}</h1>
              <p className="sr-version-history__subtitle">{t('versionHistory.subtitle')}</p>
            </div>
          </header>

          <VersionHistoryFilters
            options={resumeOptions}
            activeId={activeFilterId}
            allFilterId={allFilterId}
            onSelect={setFilter}
          />

          <section className="sr-version-history__content">
            {loading && (
              <div className="sr-version-history__loading" aria-busy="true">
                {t('versionHistory.loading')}
              </div>
            )}
            {showError && (
              <div className="sr-version-history__error">
                <p>{t('versionHistory.errorLoad')}</p>
                <Button variant="secondary" onClick={() => refetch()}>
                  {t('versionHistory.retry')}
                </Button>
              </div>
            )}
            {!loading && !showError && showEmpty && <VersionHistoryEmptyState />}
            {!loading && !showError && !showEmpty && (
              <VersionHistoryList
                items={versions}
                onView={handleView}
                onRestore={handleRestore}
              />
            )}
          </section>
        </div>
      </main>

      <Modal
        open={!!viewModalItem}
        title={viewModalItem ? `${viewModalItem.resumeTitle} — v${viewModalItem.version}` : ''}
        subtitle={
          viewModalItem
            ? formatDate(viewModalItem.createdAt, i18n.language)
            : undefined
        }
        onClose={() => setViewModalItem(null)}
      >
        {viewModalItem && (
          <div className="sr-version-view-modal">
            <p className="sr-version-view-modal__score">
              {t('versionHistory.score')}: <strong>{viewModalItem.score}</strong>
            </p>
            {viewModalItem.changes.length > 0 && (
              <>
                <h4 className="sr-version-view-modal__changes-title">
                  {t('versionHistory.viewModalChanges')}
                </h4>
                <ul className="sr-version-view-modal__changes-list">
                  {viewModalItem.changes.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </>
            )}
            <p className="sr-version-view-modal__hint">{t('versionHistory.viewModalHint')}</p>
          </div>
        )}
      </Modal>

      <Modal
        open={!!restoreModalItem}
        title={t('versionHistory.restoreModalTitle')}
        subtitle={t('versionHistory.restoreModalSubtitle')}
        onClose={() => setRestoreModalItem(null)}
      >
        {restoreModalItem && (
          <div className="sr-version-restore-modal">
            <p className="sr-version-restore-modal__text">
              {t('versionHistory.restoreModalText', {
                title: restoreModalItem.resumeTitle,
                version: restoreModalItem.version,
              })}
            </p>
            <div className="sr-version-restore-modal__actions">
              <Button variant="secondary" onClick={() => setRestoreModalItem(null)}>
                {t('common.cancel')}
              </Button>
              <Button variant="primary" onClick={() => void confirmRestore()} disabled={restoring}>
                {restoring ? t('versionHistory.restoring') : t('versionHistory.restoreConfirm')}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </AppShell>
  );
}
