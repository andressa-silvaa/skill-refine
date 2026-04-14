import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  useVersionHistory,
  VersionHistoryFilters,
  VersionHistoryList,
  VersionHistoryEmptyState,
  VersionViewModal,
  versionHistoryApi,
} from '@/features/version-history';
import { useResumes } from '@/features/resume';
import { Button, Modal } from '@/shared/ui';
import { notify } from '@/shared/lib/notify';

import type { VersionHistoryItem } from '@/features/version-history';

import '@/shared/ui/sr-controls/SrControls.css';
import './VersionHistoryPage.css';

export function VersionHistoryPage() {
  const { t } = useTranslation();
  const resumes = useResumes();
  const resumeOptions = useMemo(
    () => resumes.viewModels.map((vm) => ({ id: vm.id, title: vm.name })),
    [resumes.viewModels]
  );
  const {
    versions,
    resumeOptions: historyResumeOptions,
    activeFilterId,
    setFilter,
    allFilterId,
    loading,
    error,
    refetch,
  } = useVersionHistory({ resumeOptions });

  const [viewModalItem, setViewModalItem] = useState<VersionHistoryItem | null>(null);
  const [restoreModalItem, setRestoreModalItem] = useState<VersionHistoryItem | null>(null);
  const [restoring, setRestoring] = useState(false);

  const confirmRestore = async () => {
    if (!restoreModalItem) return;
    setRestoring(true);
    try {
      await versionHistoryApi.restore(restoreModalItem.resumeId, restoreModalItem.id);
      notify.success(t('versionHistory.restoreSuccess'));
      setRestoreModalItem(null);
      refetch();
      void resumes.reload({ force: true });
    } catch {
      notify.error(t('versionHistory.restoreFailed'));
    } finally {
      setRestoring(false);
    }
  };

  const showEmpty = !loading && versions.length === 0;
  const showError = Boolean(error);

  return (
    <>
      <main className="sr-version-history" aria-label={t('versionHistory.mainAria')}>
        <div className="sr-version-history__container">
          <header className="sr-version-history__header">
            <div>
              <h1 className="sr-version-history__h1">{t('versionHistory.title')}</h1>
              <p className="sr-version-history__subtitle">{t('versionHistory.subtitle')}</p>
            </div>
          </header>

          <VersionHistoryFilters
            options={historyResumeOptions}
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
                onView={setViewModalItem}
                onRestore={setRestoreModalItem}
              />
            )}
          </section>
        </div>
      </main>

      <VersionViewModal
        open={!!viewModalItem}
        item={viewModalItem}
        onClose={() => setViewModalItem(null)}
      />

      <Modal
        open={!!restoreModalItem}
        title={t('versionHistory.restoreModalTitle')}
        subtitle={t('versionHistory.restoreModalSubtitle')}
        onClose={() => setRestoreModalItem(null)}
        width={420}
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
              <Button
                variant="primary"
                onClick={() => void confirmRestore()}
                disabled={restoring}
              >
                {restoring ? t('versionHistory.restoring') : t('versionHistory.restoreConfirm')}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
