export type DashboardSummary = {
  userName: string;
  totalResumes: number;
  completeResumes: number;
  draftResumes: number;
  lastAnalysisLabel: string;
  lastAnalyzedResumeTitle: string;
  averageScore: number;
  averageScoreDelta: number;
  pendingSuggestions: number;
  highPrioritySuggestions: number;
};

export type ScorePoint = {
  month: string;
  score: number;
};

export type Competency = {
  label: string;
  value: number;
};

export type RecentResume = {
  id: string;
  title: string;
  updatedAtRelative: string;
  score: number | null;
};

export type AiInsight = {
  id: string;
  icon: string;
  title: string;
  description: string;
  type: 'keywords' | 'experience' | 'format' | 'structure' | 'generic';
};

export type DashboardData = {
  summary: DashboardSummary;
  scoreEvolution: ScorePoint[];
  competencies: Competency[];
  recentResumes: RecentResume[];
  aiInsights: AiInsight[];
};

const MOCK_DATA: DashboardData = {
  summary: {
    userName: 'Maria',
    totalResumes: 5,
    completeResumes: 2,
    draftResumes: 3,
    lastAnalysisLabel: 'Hoje',
    lastAnalyzedResumeTitle: 'Desenvolvedor Full Stack',
    averageScore: 78,
    averageScoreDelta: 12,
    pendingSuggestions: 8,
    highPrioritySuggestions: 3,
  },
  scoreEvolution: [
    { month: 'Jan', score: 52 },
    { month: 'Fev', score: 59 },
    { month: 'Mar', score: 63 },
    { month: 'Abr', score: 68 },
    { month: 'Mai', score: 74 },
    { month: 'Jun', score: 78 },
  ],
  competencies: [
    { label: 'Hard Skills', value: 82 },
    { label: 'Soft Skills', value: 65 },
    { label: 'Clareza', value: 74 },
    { label: 'ATS', value: 88 },
    { label: 'Formato', value: 91 },
    { label: 'Palavras-chave', value: 70 },
  ],
  recentResumes: [
    { id: '1', title: 'Desenvolvedor Full Stack', updatedAtRelative: '2 dias atrás', score: 78 },
    { id: '2', title: 'Product Manager', updatedAtRelative: '5 dias atrás', score: 64 },
    { id: '3', title: 'UX Designer', updatedAtRelative: '1 semana atrás', score: null },
  ],
  aiInsights: [
    {
      id: '1',
      icon: 'fa-solid fa-key',
      type: 'keywords',
      title: 'Palavras-chave',
      description: 'Adicione mais termos técnicos relevantes para a vaga desejada.',
    },
    {
      id: '2',
      icon: 'fa-solid fa-chart-line',
      type: 'experience',
      title: 'Experiência',
      description: 'Quantifique suas conquistas com números e métricas.',
    },
    {
      id: '3',
      icon: 'fa-solid fa-circle-check',
      type: 'format',
      title: 'Formato',
      description: 'Seu currículo está 90% otimizado para sistemas ATS.',
    },
  ],
};

export function useDashboardMock(): DashboardData {
  return MOCK_DATA;
}
