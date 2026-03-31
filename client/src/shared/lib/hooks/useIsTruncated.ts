import { useEffect, useRef, useState } from 'react';

/** Horizontal overflow (single-line ellipsis). Re-runs when `contentKey` changes. */
export function useIsTruncated<T extends HTMLElement = HTMLElement>(contentKey?: unknown) {
  const ref = useRef<T | null>(null);
  const [isTruncated, setIsTruncated] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const checkTruncation = () => {
      setIsTruncated(element.scrollWidth > element.clientWidth);
    };

    checkTruncation();

    const resizeObserver = new ResizeObserver(checkTruncation);
    resizeObserver.observe(element);

    return () => {
      resizeObserver.disconnect();
    };
  }, [contentKey]);

  return { ref, isTruncated };
}

/** True when multi-line content is clamped (e.g. -webkit-line-clamp). Re-runs when `contentKey` changes. */
export function useIsVerticallyClamped<T extends HTMLElement = HTMLElement>(contentKey?: unknown) {
  const ref = useRef<T | null>(null);
  const [isClamped, setIsClamped] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const check = () => {
      setIsClamped(element.scrollHeight > element.clientHeight + 1);
    };

    check();
    const resizeObserver = new ResizeObserver(check);
    resizeObserver.observe(element);

    return () => {
      resizeObserver.disconnect();
    };
  }, [contentKey]);

  return { ref, isClamped };
}
