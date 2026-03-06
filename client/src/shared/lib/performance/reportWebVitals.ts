import type { ReportHandler } from 'web-vitals';

declare global {
  interface Window {
    __srWebVitals?: Record<string, number>;
  }
}

export function reportWebVitals(onPerfEntry?: ReportHandler) {
  const reporter: ReportHandler = (metric) => {
    if (process.env.NODE_ENV === 'development') {
      window.__srWebVitals = {
        ...(window.__srWebVitals || {}),
        [metric.name]: Math.round(metric.value * 100) / 100,
      };
      if (!onPerfEntry) {
        // Dev-only baseline helper.
        console.info('[web-vitals]', metric.name, metric.value);
      }
    }
    if (onPerfEntry) {
      onPerfEntry(metric);
    }
  };

  import('web-vitals').then(({ getCLS, getFCP, getFID, getLCP, getTTFB }) => {
    getCLS(reporter);
    getFID(reporter);
    getFCP(reporter);
    getLCP(reporter);
    getTTFB(reporter);
  });
}


