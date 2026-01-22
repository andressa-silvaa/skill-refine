import { useState, useCallback } from 'react';

import type { ResumeData } from '@/entities/resume';

export function useResumePreview() {
  const [isOpen, setIsOpen] = useState(false);
  const [previewData, setPreviewData] = useState<ResumeData | null>(null);

  const openPreview = useCallback((data: ResumeData) => {
    setPreviewData(data);
    setIsOpen(true);
  }, []);

  const closePreview = useCallback(() => {
    setIsOpen(false);
  }, []);

  return {
    isOpen,
    previewData,
    openPreview,
    closePreview,
  };
}
