import { useEffect, useState } from 'react';

export function useMediaQuery(query: string) {
  const getMatches = () => (typeof window !== 'undefined' ? window.matchMedia(query).matches : false);
  const [matches, setMatches] = useState(getMatches);

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);

    onChange();
    // TS (lib.dom) pode tipar MediaQueryList sem addListener/removeListener (deprecated),
    // então usamos fallback via `any` para compatibilidade com browsers antigos.
    if (typeof mql.addEventListener === 'function') mql.addEventListener('change', onChange);
    else (mql as any).addListener?.(onChange);

    return () => {
      if (typeof mql.removeEventListener === 'function') mql.removeEventListener('change', onChange);
      else (mql as any).removeListener?.(onChange);
    };
  }, [query]);

  return matches;
}


