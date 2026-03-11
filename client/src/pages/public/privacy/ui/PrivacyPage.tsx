import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { useTranslation } from 'react-i18next';

import { DocumentPage } from '@/shared/ui';

export function PrivacyPage() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  useEffect(() => {
    document.title = 'Privacy Policy - Skill Refine';
    return () => {
      document.title = 'Skill Refine';
    };
  }, []);

  const sections = [
    'dataCollected',
    'purpose',
    'storage',
    'sharing',
    'rights',
    'security',
  ] as const;

  return (
    <DocumentPage
      title={t('legal.privacy.title')}
      onBack={() => navigate(-1)}
    >
      {sections.map((key) => (
        <section key={key}>
          <h2>{t(`legal.privacy.sections.${key}.title`)}</h2>
          <p>{t(`legal.privacy.sections.${key}.body`)}</p>
        </section>
      ))}
    </DocumentPage>
  );
}
