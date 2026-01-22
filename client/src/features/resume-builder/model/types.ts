export type BuilderStep = 'theme' | 'basic' | 'contact' | 'experience' | 'education' | 'skills' | 'languages' | 'summary' | 'review';

export type StepConfig = {
  id: BuilderStep;
  label: string;
  order: number;
};

export const BUILDER_STEPS: StepConfig[] = [
  { id: 'theme', label: 'Tema', order: 1 },
  { id: 'basic', label: 'Básico', order: 2 },
  { id: 'contact', label: 'Contato', order: 3 },
  { id: 'experience', label: 'Experiência', order: 4 },
  { id: 'education', label: 'Formação', order: 5 },
  { id: 'skills', label: 'Habilidades', order: 6 },
  { id: 'languages', label: 'Idiomas', order: 7 },
  { id: 'summary', label: 'Resumo', order: 8 },
  { id: 'review', label: 'Revisão', order: 9 },
];
