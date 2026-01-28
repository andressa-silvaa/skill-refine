import { getResumeThemeById } from '@/entities/resume';
import { useResumeBuilder } from '@/features/resume-builder';

import { ThemeSelectionStep } from './ThemeSelectionStep';
import { BasicInfoStep } from './BasicInfoStep';
import { ContactStep } from './ContactStep';
import { ExperienceStep } from './ExperienceStep';
import { EducationStep } from './EducationStep';
import { SkillsStep } from './SkillsStep';
import { LanguagesStep } from './LanguagesStep';
import { SummaryStep } from './SummaryStep';
import { ReviewStep } from './ReviewStep';

type BuilderState = ReturnType<typeof useResumeBuilder>;

type Props = {
  builder: BuilderState;
  onStepEdit: (stepId: string) => void;
};

export function ResumeBuilderStepContent(props: Props) {
  const { builder, onStepEdit } = props;
  const validationProps = {
    getError: (path: string) => builder.serverErrors[path] ?? builder.errors[path],
    shouldShowError: (path: string) => builder.shouldShowError(path, builder.currentStep),
    onFieldTouched: builder.markFieldTouched,
  };

  switch (builder.currentStep) {
    case 'theme':
      const currentTheme = getResumeThemeById(builder.data.themeId);
      return (
        <ThemeSelectionStep
          theme={currentTheme}
          selectedId={builder.data.themeId}
          onSelect={(id) => {
            const theme = getResumeThemeById(id);
            builder.updateData({ themeId: id, themePaletteId: theme.defaultPaletteId });
          }}
          selectedPaletteId={builder.data.themePaletteId}
          onSelectPalette={(paletteId) => {
            builder.updateData({ themePaletteId: paletteId });
          }}
          errorMessage={validationProps.shouldShowError('themeId') ? validationProps.getError('themeId') : undefined}
          paletteErrorMessage={validationProps.shouldShowError('themePaletteId') ? validationProps.getError('themePaletteId') : undefined}
        />
      );
    case 'basic':
      return <BasicInfoStep data={builder.data} onChange={builder.updateData} {...validationProps} />;
    case 'contact':
      return <ContactStep contact={builder.data.contact} onChange={(contact) => builder.updateData({ contact })} {...validationProps} />;
    case 'experience':
      return (
        <ExperienceStep
          experiences={builder.data.experiences}
          onChange={(experiences) => builder.updateData({ experiences })}
          {...validationProps}
        />
      );
    case 'education':
      return (
        <EducationStep
          educations={builder.data.educations}
          onChange={(educations) => builder.updateData({ educations })}
          {...validationProps}
        />
      );
    case 'skills':
      return (
        <SkillsStep
          skills={builder.data.skills}
          onChange={(skills) => builder.updateData({ skills })}
          showLevels={builder.showSkillLevels}
          onToggleShowLevels={(next) => {
            builder.setShowSkillLevels(next);
            if (!next) {
              builder.updateData({ skills: builder.data.skills.map((skill) => ({ ...skill, level: undefined })) });
            }
          }}
          {...validationProps}
        />
      );
    case 'languages':
      return (
        <LanguagesStep
          languages={builder.data.languages}
          onChange={(languages) => builder.updateData({ languages })}
          {...validationProps}
        />
      );
    case 'summary':
      return <SummaryStep summary={builder.data.summary} onChange={(summary) => builder.updateData({ summary })} {...validationProps} />;
    case 'review':
      return <ReviewStep data={builder.data} onEdit={onStepEdit} />;
    default:
      return null;
  }
}
