import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { Button, Input, CustomSelect } from '@/shared/ui';
import type { Language, LanguageLevel } from '@/entities/resume';

import './LanguagesStep.css';

type Props = {
  languages: Language[];
  onChange: (languages: Language[]) => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
};

export function LanguagesStep(props: Props) {
  const { languages, onChange, getError, shouldShowError, onFieldTouched } = props;
  const { t } = useTranslation();

  const levelOptions = useMemo(
    () => [
      { value: 'basic', label: t('resume.languagesStepLevelBasic') },
      { value: 'intermediate', label: t('resume.languagesStepLevelIntermediate') },
      { value: 'advanced', label: t('resume.languagesStepLevelAdvanced') },
      { value: 'fluent', label: t('resume.languagesStepLevelFluent') },
      { value: 'native', label: t('resume.languagesStepLevelNative') },
    ],
    [t]
  );

  const addLanguage = () => {
    const newLang: Language = {
      id: `lang-${Date.now()}`,
      name: '',
      level: 'intermediate',
    };
    onChange([...languages, newLang]);
  };

  const removeLanguage = (id: string) => {
    onChange(languages.filter((l) => l.id !== id));
  };

  const updateLanguage = (id: string, updates: Partial<Language>) => {
    onChange(languages.map((l) => (l.id === id ? { ...l, ...updates } : l)));
  };

  return (
    <div className="sr-languages-step">
      <div className="sr-languages-step__header">
        <h3 className="sr-languages-step__title">{t('resume.languagesStepTitle')}</h3>
        <p className="sr-languages-step__subtitle">{t('resume.languagesStepSubtitle')}</p>
      </div>

      <div className="sr-languages-step__list">
        {languages.map((lang, index) => (
          <LanguageCard
            key={lang.id}
            language={lang}
            index={index}
            onUpdate={(updates) => updateLanguage(lang.id, updates)}
            onRemove={() => removeLanguage(lang.id)}
            getError={getError}
            shouldShowError={shouldShowError}
            onFieldTouched={onFieldTouched}
            levelOptions={levelOptions}
          />
        ))}
      </div>

      <Button variant="secondary" onClick={addLanguage}>
        <i className="fa-solid fa-plus" aria-hidden />
        {t('resume.languagesStepAdd')}
      </Button>
    </div>
  );
}

type LanguageCardProps = {
  language: Language;
  index: number;
  onUpdate: (updates: Partial<Language>) => void;
  onRemove: () => void;
  getError: (path: string) => string | undefined;
  shouldShowError: (path: string) => boolean;
  onFieldTouched: (path: string) => void;
  levelOptions: { value: string; label: string }[];
};

function LanguageCard(props: LanguageCardProps) {
  const { language, index, onUpdate, onRemove, getError, shouldShowError, onFieldTouched, levelOptions } = props;
  const { t } = useTranslation();
  const basePath = `languages.${index}`;
  const nameError = shouldShowError(`${basePath}.name`) ? getError(`${basePath}.name`) : undefined;
  const levelError = shouldShowError(`${basePath}.level`) ? getError(`${basePath}.level`) : undefined;

  return (
    <div className="sr-language-card">
      <div className="sr-language-card__row">
        <Input
          label={`${t('resume.languagesStepTitle')} *`}
          placeholder={t('resume.languagesStepNamePlaceholder')}
          value={language.name}
          onChange={(e) => onUpdate({ name: e.target.value })}
          onBlur={() => onFieldTouched(`${basePath}.name`)}
          error={nameError}
        />
        <CustomSelect
          label={t('resume.languagesStepLevelBasic').replace('Básico', 'Nível *')}
          options={levelOptions}
          value={language.level}
          onChange={(value) => {
            onUpdate({ level: value as LanguageLevel });
            onFieldTouched(`${basePath}.level`);
          }}
          error={levelError}
        />
      </div>
      <Button variant="ghost" onClick={onRemove}>
        <i className="fa-solid fa-trash" aria-hidden />
        {t('resume.remove')}
      </Button>
    </div>
  );
}
