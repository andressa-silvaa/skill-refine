export const dashboardDomain = {
  dashboard: {
    mainAria: 'Dashboard Page',
    greeting: 'Welcome, {{name}}! ✨',
    subtitle: 'See how your resumes are performing.',
    newResume: 'New Resume',
    noAnalysis: 'No analysis',
    stats: {
      aria: 'Key metrics',
      totalResumes: 'Resumes Created',
      totalResumesSub: '{{complete}} complete, {{draft}} drafts',
      lastAnalysis: 'Last AI Analysis',
      averageScore: 'Average Score',
      pendingSuggestions: 'Pending Suggestions',
      pendingSuggestionsSub: '{{count}} high priority',
    },
    charts: {
      aria: 'Score evolution and competency charts',
    },
    bottom: {
      aria: 'Recent resumes and AI insights',
    },
    sections: {
      scoreEvolution: 'Score Evolution',
      competencies: 'Competency Areas',
      recentResumes: 'Recent Resumes',
      aiInsights: 'AI Insights',
    },
    actions: {
      viewAll: 'View all',
      analyze: 'Analyze',
    },
  },
} as const;
