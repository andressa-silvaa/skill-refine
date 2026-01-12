import { Card, Skeleton } from '@/shared/ui';

import './ResumesSkeleton.css';

type Props = {
  view: 'grid' | 'list';
};

export function ResumesSkeleton(props: Props) {
  const { view } = props;
  if (view === 'list') {
    return (
      <div className="sr-resumes-skeleton__list" aria-hidden>
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="sr-resumes-skeleton__row">
            <Skeleton height={14} width="50%" />
            <Skeleton height={14} width="22%" />
            <Skeleton height={14} width="36%" className="sr-resumes-skeleton__hide-sm" />
            <Skeleton height={14} width="18%" />
            <Skeleton height={34} width={86} />
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="sr-resumes-skeleton__grid" aria-hidden>
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i} className="sr-resumes-skeleton__card">
          <div className="sr-resumes-skeleton__head">
            <Skeleton width={46} height={46} radius={14} />
            <div style={{ flex: 1 }}>
              <Skeleton height={14} width="70%" />
              <div style={{ height: 8 }} />
              <Skeleton height={12} width="46%" />
            </div>
          </div>
          <Skeleton height={26} width={90} radius={999} />
          <div className="sr-resumes-skeleton__chips">
            <Skeleton height={26} width={70} radius={999} />
            <Skeleton height={26} width={86} radius={999} />
            <Skeleton height={26} width={54} radius={999} />
          </div>
        </Card>
      ))}
    </div>
  );
}
