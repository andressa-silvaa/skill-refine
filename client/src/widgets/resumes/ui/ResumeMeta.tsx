import type { ResumeViewModel } from '@/entities/resume';
import { Badge, Chip } from '@/shared/ui';

import './ResumeMeta.css';

type Props = {
  vm: ResumeViewModel;
  compact?: boolean;
};

export function ResumeMeta(props: Props) {
  const { vm, compact = false } = props;

  return (
    <div className={`sr-resume-meta${compact ? ' is-compact' : ''}`}>
      <div className="sr-resume-meta__top">
        <Badge tone={vm.statusTone}>{vm.statusLabel}</Badge>
        <div className="sr-resume-meta__score" aria-label={`Score ${vm.scoreLabel}`}>
          <i className="fa-solid fa-star" aria-hidden />
          <span className="sr-resume-meta__score-value">{vm.scoreLabel}</span>
        </div>
      </div>

      {!compact ? (
        <div className="sr-resume-meta__tags" aria-label="Habilidades">
          {vm.tagsVisible.map((t) => (
            <Chip key={t}>{t}</Chip>
          ))}
          {vm.tagsOverflow ? <Chip>{`+${vm.tagsOverflow}`}</Chip> : null}
        </div>
      ) : null}
    </div>
  );
}
