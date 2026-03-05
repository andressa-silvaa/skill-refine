export type DashboardSummaryResponse = {
  summary: {
    totalResumes: number;
    completeResumes: number;
    draftResumes: number;
    lastAnalysisAt: string | null;
    lastAnalyzedResumeId: string | null;
    lastAnalyzedResumeTitle: string | null;
    averageScore: number | null;
    averageScoreDelta: number | null;
    pendingSuggestions: number;
    highPrioritySuggestions: number;
  };
  scoreEvolution: Array<{
    period: string;
    score: number;
  }>;
  competencies: Array<{
    key: 'hardSkills' | 'softSkills' | 'clarity' | 'ats' | 'format' | 'keywords' | string;
    value: number;
  }>;
  recentResumes: Array<{
    id: string;
    name: string;
    updatedAt: string | null;
    status: string;
    score: number | null;
  }>;
  aiInsights: Array<{
    id: string;
    key: string;
    priority: 'high' | 'medium' | 'low' | string;
    count: number;
    resumeId: string | null;
    resumeTitle: string | null;
    analysisId: string | null;
    createdAt: string | null;
    params?: Record<string, string>;
  }>;
};

