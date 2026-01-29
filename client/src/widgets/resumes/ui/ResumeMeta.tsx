import { useTranslation } from 'react-i18next';

import type { ResumeViewModel } from '@/entities/resume';
import { Badge, Chip } from '@/shared/ui';

import './ResumeMeta.css';

type Props = {
  vm: ResumeViewModel;
  compact?: boolean;
};

export function ResumeMeta(props: Props) {
  const { vm, compact = false } = props;
  const { t } = useTranslation();

  return (
    <div className={`sr-resume-meta${compact ? ' is-compact' : ''}`}>
      <div className="sr-resume-meta__top">
        <Badge tone={vm.statusTone}>{vm.statusLabel}</Badge>
        <div className="sr-resume-meta__score" aria-label={t('resume.scoreLabel', { value: vm.scoreLabel })}>
          <i className="fa-solid fa-star" aria-hidden />
          <span className="sr-resume-meta__score-value">{vm.scoreLabel}</span>
        </div>
      </div>

      {!compact ? (
        <div className="sr-resume-meta__tags" aria-label={t('resume.skillsAria')}>
          {vm.tagsVisible.map((t, i) => (
            <Chip key={`skill-${i}-${t}`} className="sr-resume-meta__chip">{t}</Chip>
          ))}
          {vm.tagsOverflow > 0 ? <span className="sr-resume-meta__ellipsis" aria-hidden>...</span> : null}
        </div>
      ) : null}
    </div>
  );
}
