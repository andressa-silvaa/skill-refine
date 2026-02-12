import { useCallback, useEffect, useState } from 'react';

export function useResumeWizardPreview(wizardOpen: boolean) {
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  useEffect(() => {
    if (!wizardOpen && isPreviewOpen) setIsPreviewOpen(false);
  }, [wizardOpen, isPreviewOpen]);

  const openPreview = useCallback(() => setIsPreviewOpen(true), []);
  const closePreview = useCallback(() => setIsPreviewOpen(false), []);

  return { isPreviewOpen, openPreview, closePreview };
}
