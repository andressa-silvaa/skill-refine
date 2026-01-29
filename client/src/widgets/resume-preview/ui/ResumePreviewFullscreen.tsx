import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';

import type { ResumeData } from '@/entities/resume';
import { stressResumeData } from '@/entities/resume/mocks/stressResume';
import { getResumeThemeById } from '@/entities/resume';
import { ResumeColorEditor } from '@/features/resume-color-editor';

import { ResumePreviewContent } from './ResumePreviewContent';
import './ResumePreviewFullscreen.css';

type Props = {
  open: boolean;
  data: ResumeData;
  onClose: () => void;
  enableStressToggle?: boolean;
  onUpdateData?: (updates: Partial<ResumeData>) => void;
};

export function ResumePreviewFullscreen(props: Props) {
  const { open, data, onClose, enableStressToggle = false, onUpdateData } = props;
  const { t } = useTranslation();
  const [useStress, setUseStress] = useState(false);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (!open) setUseStress(false);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose, open]);

  const previewData = useMemo(
    () =>
      useStress
        ? {
            ...stressResumeData,
            themeId: data.themeId,
            themePaletteId: data.themePaletteId,
          }
        : data,
    [data, useStress]
  );
  const theme = getResumeThemeById(previewData.themeId);

  if (!open) return null;

  const portalRoot = document.querySelector('[data-sr-theme-scope]') ?? document.body;

  return createPortal(
    <div className="sr-resume-preview-fullscreen" role="dialog" aria-modal="true" aria-label={t('resume.previewTitle')}>
      <div className="sr-resume-preview-fullscreen__header">
        <div className="sr-resume-preview-fullscreen__header-left">
          <span className="sr-resume-preview-fullscreen__badge">{t('resume.previewBadge')}</span>
          <span className="sr-resume-preview-fullscreen__title">{t('resume.previewTitle')}</span>
        </div>
        {enableStressToggle ? (
          <button
            type="button"
            className="sr-resume-preview-fullscreen__stress"
            aria-pressed={useStress}
            onClick={() => setUseStress((prev) => !prev)}
          >
            {useStress ? t('resume.previewBack') : t('resume.previewStress')}
          </button>
        ) : null}
        <button type="button" className="sr-resume-preview-fullscreen__close" aria-label={t('resume.previewClose')} onClick={onClose}>
          ×
        </button>
      </div>
      <div className="sr-resume-preview-fullscreen__content">
        <div className="sr-resume-preview-fullscreen__layout">
          {onUpdateData ? (
            <aside className="sr-resume-preview-fullscreen__panel">
              <ResumeColorEditor
                theme={theme}
                paletteId={previewData.themePaletteId}
                onChange={onUpdateData}
              />
            </aside>
          ) : null}
          <div className="sr-resume-preview-fullscreen__preview">
            <ResumePreviewContent data={previewData} />
          </div>
        </div>
      </div>
    </div>,
    portalRoot
  );
}
