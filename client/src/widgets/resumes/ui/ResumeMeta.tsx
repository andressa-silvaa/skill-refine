import { memo } from 'react';
import { useTranslation } from 'react-i18next';

import type { ResumeViewModel } from '@/entities/resume';
import type { LatestAnalysisInfo } from '@/features/ai-analysis';
import { Badge, Chip } from '@/shared/ui';

import './ResumeMeta.css';

type Props = {
  vm: ResumeViewModel;
  compact?: boolean;
  analysisInfo?: LatestAnalysisInfo | null;
};

export const ResumeMeta = memo(function ResumeMeta(props: Props) {
  const { vm, compact = false, analysisInfo } = props;
  const { t } = useTranslation();

  const isAnalyzing =
    analysisInfo?.status === 'pending' || analysisInfo?.status === 'running';
  const aiScoreLabel =
    analysisInfo?.status === 'done' && analysisInfo.score != null
      ? t('analysis.cardScore', { score: analysisInfo.score })
      : null;

  return (
    <div className={`sr-resume-meta${compact ? ' is-compact' : ''}`}>
      <div className="sr-resume-meta__top">
        <Badge tone={vm.statusTone}>{vm.statusLabel}</Badge>
        {isAnalyzing && (
          <span className="sr-resume-meta__ai-status" aria-live="polite">
            {t('analysis.status.running')}
          </span>
        )}
        {aiScoreLabel && !isAnalyzing && (
          <span className="sr-resume-meta__ai-score" aria-label={aiScoreLabel}>
            {aiScoreLabel}
          </span>
        )}
        {!aiScoreLabel && !isAnalyzing && (
          <div className="sr-resume-meta__score" aria-label={t('resume.scoreLabel', { value: vm.scoreLabel })}>
            <i className="fa-solid fa-star" aria-hidden />
            <span className="sr-resume-meta__score-value">{vm.scoreLabel}</span>
          </div>
        )}
      </div>

      {!compact ? (
        <div className="sr-resume-meta__tags" aria-label={t('resume.skillsAria')}>
          {vm.tagsVisible.map((tagLabel, i) => (
            <Chip key={`skill-${i}-${tagLabel}`} className="sr-resume-meta__chip">
              {tagLabel}
            </Chip>
          ))}
          {vm.tagsOverflow > 0 ? <span className="sr-resume-meta__ellipsis" aria-hidden>...</span> : null}
        </div>
      ) : null}
    </div>
  );
});
