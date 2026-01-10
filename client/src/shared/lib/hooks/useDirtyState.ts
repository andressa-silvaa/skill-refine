import { useMemo, useState } from 'react';

type Options<T> = {
  isEqual?: (a: T, b: T) => boolean;
};

function defaultIsEqual<T>(a: T, b: T) {
  return Object.is(a, b);
}

export function useDirtyState<T>(initialDraft: T, options?: Options<T>) {
  const isEqual = options?.isEqual ?? defaultIsEqual;

  const [server, setServer] = useState<T | null>(null);
  const [draft, setDraft] = useState<T>(initialDraft);

  const isDirty = useMemo(() => {
    if (server === null) return false;
    return !isEqual(draft, server);
  }, [draft, isEqual, server]);

  const acceptServer = (next: T) => {
    setServer(next);
    setDraft(next);
  };

  const resetDraft = () => {
    if (server === null) return;
    setDraft(server);
  };

  return {
    server,
    draft,
    setDraft,
    isDirty,
    acceptServer,
    resetDraft,
  };
}
