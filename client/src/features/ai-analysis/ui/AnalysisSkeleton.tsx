import { useTranslation } from 'react-i18next';

import { Card, Skeleton } from '@/shared/ui';

import './AnalysisSkeleton.css';

export function AnalysisSkeleton() {
  const { t } = useTranslation();

  return (
    <div className="sr-analysis-skeleton" role="status" aria-live="polite" aria-label={t('analysis.loading')}>
      <div className="sr-analysis-skeleton__metrics">
        <Card className="sr-analysis-skeleton__score">
          <Skeleton width={88} height={88} radius={999} className="sr-analysis-skeleton__ring" />
          <Skeleton width={80} height={12} radius={8} />
          <Skeleton width={60} height={12} radius={8} />
        </Card>
        <Card className="sr-analysis-skeleton__card">
          <Skeleton width={40} height={40} radius={12} />
          <Skeleton width={60} height={11} radius={6} />
          <Skeleton width={48} height={20} radius={8} />
          <Skeleton width={70} height={22} radius={999} />
        </Card>
        <Card className="sr-analysis-skeleton__card">
          <Skeleton width={40} height={40} radius={12} />
          <Skeleton width={50} height={11} radius={6} />
          <Skeleton width={48} height={20} radius={8} />
          <Skeleton width={70} height={22} radius={999} />
        </Card>
        <Card className="sr-analysis-skeleton__card">
          <Skeleton width={40} height={40} radius={12} />
          <Skeleton width={60} height={11} radius={6} />
          <Skeleton width={90} height={18} radius={8} />
          <Skeleton width={70} height={22} radius={999} />
        </Card>
      </div>
      <div className="sr-analysis-skeleton__lists">
        <Card className="sr-analysis-skeleton__list">
          <Skeleton width={120} height={14} radius={6} />
          <Skeleton width="100%" height={52} radius={12} />
          <Skeleton width="95%" height={52} radius={12} />
          <Skeleton width="90%" height={52} radius={12} />
        </Card>
        <Card className="sr-analysis-skeleton__list">
          <Skeleton width={140} height={14} radius={6} />
          <Skeleton width="100%" height={72} radius={12} />
          <Skeleton width="98%" height={72} radius={12} />
          <Skeleton width="92%" height={72} radius={12} />
        </Card>
      </div>
    </div>
  );
}