import { useTranslation } from 'react-i18next';

import type { RecentResume } from '../model/useDashboardMock';

import './RecentResumeItem.css';

type Props = {
  item: RecentResume;
};

export function RecentResumeItem({ item }: Props) {
  const { t } = useTranslation();

  return (
    <div className="sr-dash-resume-item">
      <div className="sr-dash-resume-item__icon">
        <i className="fa-regular fa-file-lines" aria-hidden />
      </div>
      <div className="sr-dash-resume-item__info">
        <span className="sr-dash-resume-item__title">{item.title}</span>
        <span className="sr-dash-resume-item__date">{item.updatedAtRelative}</span>
      </div>
      <div className="sr-dash-resume-item__score-wrap">
        {item.score !== null ? (
          <span className="sr-dash-resume-item__score">{item.score}</span>
        ) : (
          <span className="sr-dash-resume-item__no-analysis">
            {t('dashboard.noAnalysis')}
          </span>
        )}
      </div>
      <i className="fa-solid fa-chevron-right sr-dash-resume-item__arrow" aria-hidden />
    </div>
  );
}
