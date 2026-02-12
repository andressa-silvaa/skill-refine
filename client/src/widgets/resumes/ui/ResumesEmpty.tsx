import { useTranslation } from 'react-i18next';

import { Button, Card } from '@/shared/ui';

import './ResumesEmpty.css';

type Props = {
  onCreate: () => void;
};

export function ResumesEmpty(props: Props) {
  const { onCreate } = props;
  const { t } = useTranslation();

  return (
    <Card className="sr-resumes-empty">
      <div className="sr-resumes-empty__icon" aria-hidden>
        <i className="fa-regular fa-file-lines" />
      </div>
      <h3 className="sr-resumes-empty__title">{t('resume.emptyTitle')}</h3>
      <p className="sr-resumes-empty__text">{t('resume.emptySubtitle')}</p>
      <Button variant="primary" onClick={onCreate}>
        <i className="fa-solid fa-plus" aria-hidden />
        {t('resume.emptyCta')}
      </Button>
    </Card>
  );
}
