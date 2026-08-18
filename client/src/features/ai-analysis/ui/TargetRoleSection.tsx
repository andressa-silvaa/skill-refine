import { useTranslation } from 'react-i18next';

import type { AnalysisResult } from '../model/types';
import { MetricCard } from './MetricCard';

import './TargetRoleSection.css';

type Props = {
  result: AnalysisResult;
};

export function TargetRoleSection(props: Props) {
  const { result } = props;
  const { t } = useTranslation();
  const tf = result.targetFit;
  if (!tf) {
    return null;
  }

  const fitBadge =
    tf.score >= 75 ? t('analysis.badgeExcellent') : tf.score >= 50 ? t('analysis.badgeGood') : t('analysis.badgeAttention');
  const fitTone = tf.score >= 75 ? 'success' : tf.score >= 50 ? 'neutral' : 'warning';

  return (
    <section className="sr-target-role" aria-label={t('analysis.targetFit.sectionAria')}>
      <h2 className="sr-target-role__title">{t('analysis.targetFit.sectionTitle')}</h2>
      <div className="sr-target-role__grid">
        <MetricCard
          icon={<i className="fa-solid fa-crosshairs" aria-hidden />}
          label={t('analysis.targetFit.fitCard')}
          value={`${tf.score}%`}
          badge={fitBadge}
          badgeTone={fitTone}
        />
      </div>
    </section>
  );
}
