import { useEffect, useRef } from 'react';

type Params = {
  downloadLoadingId: string | null;
  setPdfProgress: (value: number) => void;
};

export function usePdfProgressEffect(params: Params) {
  const { downloadLoadingId, setPdfProgress } = params;
  const progressRef = useRef(0);

  useEffect(() => {
    if (!downloadLoadingId) {
      setPdfProgress(0);
      progressRef.current = 0;
      return;
    }
    setPdfProgress(8);
    progressRef.current = 8;
    const interval = window.setInterval(() => {
      if (progressRef.current >= 92) return;
      const step = 3 + Math.floor(Math.random() * 6);
      progressRef.current = Math.min(92, progressRef.current + step);
      setPdfProgress(progressRef.current);
    }, 450);
    return () => window.clearInterval(interval);
  }, [downloadLoadingId, setPdfProgress]);
}
