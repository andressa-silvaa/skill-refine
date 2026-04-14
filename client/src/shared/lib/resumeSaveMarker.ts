/**
 * When a resume is saved outside the AI analysis page, that screen's useResumes() instance
 * may still hold a cached list (or miss updatedAt churn). We persist the last save so
 * analysis can re-fetch GET /analysis/latest after navigation or via event.
 */
export const RESUME_SAVE_STORAGE_KEY = 'skill-refine:last-resume-save';

export type ResumeSaveMarker = { resumeId: string; at: number };

export function markResumeContentSaved(resumeId: string): void {
  const payload: ResumeSaveMarker = { resumeId, at: Date.now() };
  try {
    localStorage.setItem(RESUME_SAVE_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    /* quota / private mode */
  }
  try {
    window.dispatchEvent(new CustomEvent('skill-refine:resume-saved', { detail: { resumeId } }));
  } catch {
    /* ignore */
  }
}

export function readResumeSaveMarker(): ResumeSaveMarker | null {
  try {
    const raw = localStorage.getItem(RESUME_SAVE_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ResumeSaveMarker>;
    if (typeof parsed.resumeId === 'string' && typeof parsed.at === 'number') {
      return { resumeId: parsed.resumeId, at: parsed.at };
    }
    return null;
  } catch {
    return null;
  }
}

export function analysisSyncStorageKey(resumeId: string): string {
  return `sr_analysis_sync_${resumeId}`;
}
