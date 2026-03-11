import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { useTranslation } from 'react-i18next';

import { DocumentPage } from '@/shared/ui';

export function TermsPage() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  useEffect(() => {
    document.title = 'Terms of Use - Skill Refine';
    return () => {
      document.title = 'Skill Refine';
    };
  }, []);

  const sections = [
    'purpose',
    'rules',
    'ip',
    'liability',
    'suspension',
  ] as const;

  return (
    <DocumentPage
      title={t('legal.terms.title')}
      onBack={() => navigate(-1)}
    >
      {sections.map((key) => (
        <section key={key}>
          <h2>{t(`legal.terms.sections.${key}.title`)}</h2>
          <p>{t(`legal.terms.sections.${key}.body`)}</p>
        </section>
      ))}
    </DocumentPage>
  );
}
