import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/shared/ui';

import './DashboardHeader.css';

type Props = {
  userName: string;
};

export function DashboardHeader({ userName }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <header className="sr-dash-header">
      <div className="sr-dash-header__text">
        <h1 className="sr-dash-header__title">
          {t('dashboard.greeting', { name: userName })}
        </h1>
        <p className="sr-dash-header__subtitle">{t('dashboard.subtitle')}</p>
      </div>
      <div className="sr-dash-header__actions">
        <Button
          variant="primary"
          onClick={() => navigate('/protected/resumes?create=1')}
        >
          <i className="fa-solid fa-plus" aria-hidden />
          {t('dashboard.newResume')}
        </Button>
      </div>
    </header>
  );
}
