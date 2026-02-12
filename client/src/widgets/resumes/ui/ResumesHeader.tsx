import { useTranslation } from 'react-i18next';

import { Button } from '@/shared/ui';

import './ResumesHeader.css';

type Props = {
  onCreate: () => void;
};

export function ResumesHeader(props: Props) {
  const { onCreate } = props;
  const { t } = useTranslation();

  return (
    <header className="sr-resumes__header">
      <div>
        <h1 className="sr-resumes__h1">{t('resume.title')}</h1>
        <p className="sr-resumes__subtitle">{t('resume.subtitle')}</p>
      </div>
      <Button variant="primary" onClick={onCreate}>
        <i className="fa-solid fa-plus" aria-hidden />
        {t('resume.newResume')}
      </Button>
    </header>
  );
}
