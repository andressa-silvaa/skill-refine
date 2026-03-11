export const notificationsDomain = {
  notifications: {
    analysisDone: 'Análisis completado para "{{name}}"',
    analysisFailed: 'Análisis fallido para "{{name}}"',
    pdfReady: 'PDF listo para "{{name}}"',
    pdfFailed: 'Error al generar PDF de "{{name}}"',
    versionRestored: 'Versión v{{version}} restaurada en "{{name}}"',
    system: 'Notificación del sistema',
    empty: 'Sin notificaciones',
    markAllRead: 'Marcar todas como leídas',
    clearAll: 'Limpar notificaciones',
    loading: 'Cargando...',
    error: 'No se pudieron cargar las notificaciones.',
  },
} as const;
