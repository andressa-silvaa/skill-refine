import type { ReportHandler } from 'web-vitals';

export function reportWebVitals(onPerfEntry?: ReportHandler) {
  if (!onPerfEntry) return;

  import('web-vitals').then(({ getCLS, getFCP, getFID, getLCP, getTTFB }) => {
    getCLS(onPerfEntry);
    getFID(onPerfEntry);
    getFCP(onPerfEntry);
    getLCP(onPerfEntry);
    getTTFB(onPerfEntry);
  });
}


