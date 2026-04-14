import { useTranslation } from 'react-i18next';

import { Card } from '@/shared/ui';
import { ScoreExplanationPopover } from './ScoreExplanationPopover';

import './ScoreCard.css';

type Props = {
  score: number;
  scoreLabel: string;
  howWeCalculateLabel: string;
  /** Ex.: score reflete qualidade do currículo, não senioridade. */
  qualityHint?: string;
};

const CIRCLE_SIZE = 88;
const STROKE_WIDTH = 6;
const RADIUS = (CIRCLE_SIZE - STROKE_WIDTH) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function ScoreCard(props: Props) {
  const { score, scoreLabel, howWeCalculateLabel, qualityHint } = props;
  const { t } = useTranslation();

  const normalizedScore = Math.min(100, Math.max(0, score));
  const strokeDashoffset = CIRCUMFERENCE - (normalizedScore / 100) * CIRCUMFERENCE;

  return (
    <Card className="sr-score-card">
      <div className="sr-score-card__ring-wrap" aria-hidden>
        <svg
          className="sr-score-card__ring"
          width="100%"
          height="100%"
          viewBox={`0 0 ${CIRCLE_SIZE} ${CIRCLE_SIZE}`}
          preserveAspectRatio="xMidYMid meet"
        >
          <circle
            className="sr-score-card__ring-bg"
            cx={CIRCLE_SIZE / 2}
            cy={CIRCLE_SIZE / 2}
            r={RADIUS}
            fill="none"
            strokeWidth={STROKE_WIDTH}
          />
          <circle
            className="sr-score-card__ring-fill"
            cx={CIRCLE_SIZE / 2}
            cy={CIRCLE_SIZE / 2}
            r={RADIUS}
            fill="none"
            strokeWidth={STROKE_WIDTH}
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            transform={`rotate(-90 ${CIRCLE_SIZE / 2} ${CIRCLE_SIZE / 2})`}
          />
        </svg>
        <span className="sr-score-card__value">{score}</span>
      </div>
      <h3 className="sr-score-card__label">{t('analysis.scoreGeneral')}</h3>
      <span className="sr-score-card__subtext">{scoreLabel}</span>
      {qualityHint ? <p className="sr-score-card__meaning">{qualityHint}</p> : null}
      <ScoreExplanationPopover triggerLabel={howWeCalculateLabel} />
    </Card>
  );
}
