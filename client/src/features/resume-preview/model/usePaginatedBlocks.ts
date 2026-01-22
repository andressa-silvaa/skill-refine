import { useEffect, useMemo, useRef, useState } from 'react';

import type { ThemeBlock } from '../ui/ThemeRenderer';

type Options = {
  pageHeight: number;
  gap: number;
};

type Result = {
  pages: ThemeBlock[][];
  register: (index: number) => (node: HTMLElement | null) => void;
};

export function usePaginatedBlocks(blocks: ThemeBlock[], options: Options): Result {
  const { pageHeight, gap } = options;
  const [heights, setHeights] = useState<number[]>([]);
  const elementsRef = useRef<(HTMLElement | null)[]>([]);
  const observerRef = useRef<ResizeObserver | null>(null);

  useEffect(() => {
    observerRef.current?.disconnect();
    observerRef.current = new ResizeObserver((entries) => {
      setHeights((prev) => {
        const next = [...prev];
        for (const entry of entries) {
          const index = elementsRef.current.indexOf(entry.target as HTMLElement);
          if (index >= 0) {
            next[index] = entry.contentRect.height;
          }
        }
        return next;
      });
    });

    elementsRef.current.forEach((el) => {
      if (el) observerRef.current?.observe(el);
    });

    return () => {
      observerRef.current?.disconnect();
    };
  }, [blocks.length]);

  const register = (index: number) => (node: HTMLElement | null) => {
    elementsRef.current[index] = node;
    if (!observerRef.current || !node) return;
    observerRef.current.observe(node);
  };

  const pages = useMemo(() => {
    const result: ThemeBlock[][] = [];
    let current: ThemeBlock[] = [];
    let currentHeight = 0;

    blocks.forEach((block, index) => {
      const blockHeight = heights[index] ?? 0;
      const extraGap = current.length > 0 ? gap : 0;
      const nextHeight = currentHeight + blockHeight + extraGap;

      if (current.length > 0 && nextHeight > pageHeight) {
        result.push(current);
        current = [block];
        currentHeight = blockHeight;
      } else {
        current.push(block);
        currentHeight = nextHeight;
      }
    });

    if (current.length > 0) result.push(current);
    if (result.length === 0) result.push([]);

    return result;
  }, [blocks, heights, pageHeight, gap]);

  return { pages, register };
}
