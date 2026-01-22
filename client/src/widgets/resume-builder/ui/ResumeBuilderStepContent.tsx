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

  switch (builder.currentStep) {
    case 'theme':
      return (
        <ThemeSelectionStep
          selectedId={builder.data.themeId}
          onSelect={(id) => {
            const theme = getResumeThemeById(id);
            builder.updateData({ themeId: id, themePaletteId: theme.defaultPaletteId });
          }}
        />
      );
    case 'basic':
      return <BasicInfoStep data={builder.data} onChange={builder.updateData} />;
    case 'contact':
      return <ContactStep contact={builder.data.contact} onChange={(contact) => builder.updateData({ contact })} />;
    case 'experience':
      return <ExperienceStep experiences={builder.data.experiences} onChange={(experiences) => builder.updateData({ experiences })} />;
    case 'education':
      return <EducationStep educations={builder.data.educations} onChange={(educations) => builder.updateData({ educations })} />;
    case 'skills':
      return <SkillsStep skills={builder.data.skills} onChange={(skills) => builder.updateData({ skills })} />;
    case 'languages':
      return <LanguagesStep languages={builder.data.languages} onChange={(languages) => builder.updateData({ languages })} />;
    case 'summary':
      return <SummaryStep summary={builder.data.summary} onChange={(summary) => builder.updateData({ summary })} />;
    case 'review':
      return <ReviewStep data={builder.data} onEdit={onStepEdit} />;
    default:
      return null;
  }
}
