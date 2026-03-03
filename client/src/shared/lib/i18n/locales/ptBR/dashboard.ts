export const dashboardDomain = {
  dashboard: {
    mainAria: 'Página do Dashboard',
    greeting: 'Bem-vinda, {{name}}! ✨',
    subtitle: 'Veja como está o desempenho dos seus currículos.',
    newResume: 'Novo Currículo',
    noAnalysis: 'Sem análise',
    stats: {
      aria: 'Métricas principais',
      totalResumes: 'Currículos Criados',
      totalResumesSub: '{{complete}} completos, {{draft}} rascunhos',
      lastAnalysis: 'Última Análise IA',
      averageScore: 'Score Médio',
      pendingSuggestions: 'Sugestões Pendentes',
      pendingSuggestionsSub: '{{count}} de alta prioridade',
    },
    charts: {
      aria: 'Gráficos de evolução e competências',
    },
    bottom: {
      aria: 'Últimos currículos e insights da IA',
    },
    sections: {
      scoreEvolution: 'Evolução do Score',
      competencies: 'Áreas de Competência',
      recentResumes: 'Últimos Currículos',
      aiInsights: 'Insights da IA',
    },
    actions: {
      viewAll: 'Ver todos',
      analyze: 'Analisar',
    },
  },
} as const;
