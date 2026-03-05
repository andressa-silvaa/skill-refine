export type DashboardSummary = {
  userName: string;
  totalResumes: number;
  completeResumes: number;
  draftResumes: number;
  lastAnalysisLabel: string;
  lastAnalyzedResumeTitle: string;
  averageScore: number | null;
  averageScoreDelta: number | null;
  pendingSuggestions: number;
  highPrioritySuggestions: number;
};

export type ScorePoint = {
  month: string;
  score: number;
};

export type Competency = {
  key: string;
  label: string;
  value: number;
};

export type RecentResume = {
  id: string;
  title: string;
  updatedAt: string | null;
  updatedAtRelative: string;
  status: string;
  score: number | null;
};

export type AiInsight = {
  id: string;
  key: string;
  icon: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  count: number;
  resumeId: string | null;
  resumeTitle: string | null;
};

export type DashboardData = {
  summary: DashboardSummary;
  scoreEvolution: ScorePoint[];
  competencies: Competency[];
  recentResumes: RecentResume[];
  aiInsights: AiInsight[];
};

