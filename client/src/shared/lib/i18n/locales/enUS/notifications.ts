export const notificationsDomain = {
  notifications: {
    analysisDone: 'Analysis completed for "{{name}}"',
    analysisFailed: 'Analysis failed for "{{name}}"',
    pdfReady: 'PDF ready for "{{name}}"',
    pdfFailed: 'PDF generation failed for "{{name}}"',
    versionRestored: 'Version v{{version}} restored for "{{name}}"',
    system: 'System notification',
    empty: 'No notifications',
    markAllRead: 'Mark all as read',
    clearAll: 'Clear notifications',
    loading: 'Loading...',
    error: 'Could not load notifications.',
  },
} as const;
