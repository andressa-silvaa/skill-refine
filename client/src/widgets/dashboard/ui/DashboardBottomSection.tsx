import type { AiInsight, RecentResume } from '../model/types';
import { DashboardInsights } from './DashboardInsights';
import { DashboardRecentResumes } from './DashboardRecentResumes';

import './DashboardBottomSection.css';

type Props = {
  recentResumes: RecentResume[];
  aiInsights: AiInsight[];
};

export function DashboardBottomSection({ recentResumes, aiInsights }: Props) {
  return (
    <div className="sr-dash-bottom-section">
      <DashboardRecentResumes items={recentResumes} />
      <DashboardInsights items={aiInsights} />
    </div>
  );
}
