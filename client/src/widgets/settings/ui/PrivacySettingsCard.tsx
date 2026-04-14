import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { privacyApi, useSessionActions } from '@/entities/session';
import { getApiErrorMessage } from '@/shared/api';
import { notify } from '@/shared/lib/notify';

import './PrivacySettingsCard.css';
import { DeleteAccountModal } from './DeleteAccountModal';

export function PrivacySettingsCard() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const { logout } = useSessionActions();

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  return (
    <section className="sr-settings__card" aria-label={t('settings.privacy')}>
      <header className="sr-settings__card-header">
        <div>
          <h2 className="sr-settings__card-title">
            <i className="fa-solid fa-lock" aria-hidden /> {t('settings.privacy')}
          </h2>
          <div className="sr-settings__muted">{t('settings.privacyMuted')}</div>
        </div>
      </header>

      <div className="sr-privacy__panel" aria-label={t('settings.privacyPanelAria')}>
        <div className="sr-privacy__panel-title">{t('settings.privacyPanelTitle')}</div>
        <p className="sr-privacy__panel-text">{t('settings.privacyPanelText')}</p>
      </div>

      <div className="sr-privacy__actions" aria-label={t('settings.dataActionsAria')}>
        <div className="sr-privacy__actions-title">{t('settings.dataActions')}</div>
        <div className="sr-privacy__links">
          <button
            type="button"
            className="sr-privacy__link sr-privacy__link--danger"
            disabled={isDeleting}
            onClick={() => {
              if (isDeleting) return;
              setDeleteOpen(true);
            }}
          >
            {t('settings.deleteAccount')}
          </button>
        </div>
      </div>

      <DeleteAccountModal
        open={deleteOpen}
        isLoading={isDeleting}
        onClose={() => {
          if (isDeleting) return;
          setDeleteOpen(false);
        }}
        onConfirm={async () => {
          if (isDeleting) return;
          setIsDeleting(true);
          try {
            await privacyApi.deleteAccount();
            await logout({ skipServer: true });
            notify.success('Sua conta foi excluída com sucesso.');
            nav('/login', { replace: true });
          } catch (e) {
            notify.error(getApiErrorMessage(e, 'Não foi possível excluir sua conta agora.'));
          } finally {
            setIsDeleting(false);
            setDeleteOpen(false);
          }
        }}
      />
    </section>
  );
}
