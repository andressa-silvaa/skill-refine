import { Button, Input, CustomSelect } from '@/shared/ui';
import type { Language, LanguageLevel } from '@/entities/resume';

import './LanguagesStep.css';

type Props = {
  languages: Language[];
  onChange: (languages: Language[]) => void;
};

const LEVEL_OPTIONS = [
  { value: 'basic', label: 'Básico' },
  { value: 'intermediate', label: 'Intermediário' },
  { value: 'advanced', label: 'Avançado' },
  { value: 'fluent', label: 'Fluente' },
  { value: 'native', label: 'Nativo' },
];

export function LanguagesStep(props: Props) {
  const { languages, onChange } = props;

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
        <h3 className="sr-languages-step__title">Idiomas</h3>
        <p className="sr-languages-step__subtitle">Adicione os idiomas que você domina</p>
      </div>

      <div className="sr-languages-step__list">
        {languages.map((lang) => (
          <LanguageCard
            key={lang.id}
            language={lang}
            onUpdate={(updates) => updateLanguage(lang.id, updates)}
            onRemove={() => removeLanguage(lang.id)}
          />
        ))}
      </div>

      <Button variant="secondary" onClick={addLanguage}>
        <i className="fa-solid fa-plus" aria-hidden />
        Adicionar idioma
      </Button>
    </div>
  );
}

type LanguageCardProps = {
  language: Language;
  onUpdate: (updates: Partial<Language>) => void;
  onRemove: () => void;
};

function LanguageCard(props: LanguageCardProps) {
  const { language, onUpdate, onRemove } = props;

  return (
    <div className="sr-language-card">
      <div className="sr-language-card__row">
        <Input
          label="Idioma"
          placeholder="Ex.: Inglês, Espanhol, Francês"
          value={language.name}
          onChange={(e) => onUpdate({ name: e.target.value })}
        />
        <CustomSelect
          label="Nível"
          options={LEVEL_OPTIONS}
          value={language.level}
          onChange={(value) => onUpdate({ level: value as LanguageLevel })}
        />
      </div>
      <Button variant="ghost" onClick={onRemove}>
        <i className="fa-solid fa-trash" aria-hidden />
        Remover
      </Button>
    </div>
  );
}
