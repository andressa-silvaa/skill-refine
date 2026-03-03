export const dashboardDomain = {
  dashboard: {
    mainAria: 'Página del Dashboard',
    greeting: '¡Bienvenida, {{name}}! ✨',
    subtitle: 'Mira cómo están rindiendo tus currículos.',
    newResume: 'Nuevo Currículo',
    noAnalysis: 'Sin análisis',
    stats: {
      aria: 'Métricas principales',
      totalResumes: 'Currículos Creados',
      totalResumesSub: '{{complete}} completos, {{draft}} borradores',
      lastAnalysis: 'Último Análisis IA',
      averageScore: 'Score Promedio',
      pendingSuggestions: 'Sugerencias Pendientes',
      pendingSuggestionsSub: '{{count}} de alta prioridad',
    },
    charts: {
      aria: 'Gráficos de evolución y competencias',
    },
    bottom: {
      aria: 'Últimos currículos e insights de la IA',
    },
    sections: {
      scoreEvolution: 'Evolución del Score',
      competencies: 'Áreas de Competencia',
      recentResumes: 'Últimos Currículos',
      aiInsights: 'Insights de la IA',
    },
    actions: {
      viewAll: 'Ver todos',
      analyze: 'Analizar',
    },
  },
} as const;
