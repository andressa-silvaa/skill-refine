import { useCallback, useState } from 'react';

type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

type Options = {
  resetOnRun?: boolean;
};

export function useAsyncRequest<TArgs extends unknown[], TResult>(
  fn: (...args: TArgs) => Promise<TResult>,
  options: Options = {}
) {
  const { resetOnRun = true } = options;

  const [status, setStatus] = useState<AsyncStatus>('idle');
  const [data, setData] = useState<TResult | null>(null);
  const [error, setError] = useState<unknown>(null);

  const run = useCallback(
    async (...args: TArgs) => {
      if (resetOnRun) {
        setData(null);
        setError(null);
      }
      setStatus('loading');
      try {
        const res = await fn(...args);
        setData(res);
        setStatus('success');
        return res;
      } catch (e) {
        setError(e);
        setStatus('error');
        throw e;
      }
    },
    [fn, resetOnRun]
  );

  const reset = useCallback(() => {
    setStatus('idle');
    setData(null);
    setError(null);
  }, []);

  return {
    run,
    reset,
    status,
    isIdle: status === 'idle',
    isLoading: status === 'loading',
    isSuccess: status === 'success',
    isError: status === 'error',
    data,
    error,
  };
}


