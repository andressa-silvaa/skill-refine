import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type Options = {
  seconds: number;
};

export function useCooldown(options: Options) {
  const { seconds } = options;
  const [remaining, setRemaining] = useState(0);
  const timerRef = useRef<number | null>(null);

  const stop = useCallback(() => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setRemaining(0);
  }, []);

  const start = useCallback((overrideSeconds?: number) => {
    stop();
    const initial = Math.max(0, Math.floor(overrideSeconds ?? seconds));
    setRemaining(initial);
    if (!initial) return;
    timerRef.current = window.setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          if (timerRef.current) window.clearInterval(timerRef.current);
          timerRef.current = null;
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, [seconds, stop]);

  useEffect(() => stop, [stop]);

  const isCoolingDown = remaining > 0;
  const label = useMemo(() => {
    if (!isCoolingDown) return null;
    return `Aguarde ${remaining}s`;
  }, [isCoolingDown, remaining]);

  return { start, stop, remaining, isCoolingDown, label };
}


