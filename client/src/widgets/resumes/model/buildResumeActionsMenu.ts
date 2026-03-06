import type { DropdownItem } from '@/shared/ui/dropdown-menu/DropdownMenu';

type Translator = (key: string, options?: Record<string, unknown>) => string;

type Params = {
  resumeId: string;
  duplicateLoadingId?: string | null;
  downloadLoadingId?: string | null;
  onEdit: (id: string) => void;
  onDuplicate: (id: string) => void;
  onExport: (id: string) => void;
  onDelete: (id: string) => void;
  onAnalyzeWithAI?: (id: string) => void;
  t: Translator;
};

export function buildResumeActionsMenu(params: Params): DropdownItem[] {
  const {
    resumeId,
    duplicateLoadingId,
    downloadLoadingId,
    onEdit,
    onDuplicate,
    onExport,
    onDelete,
    onAnalyzeWithAI,
    t,
  } = params;

  const items: DropdownItem[] = [
    {
      key: 'edit',
      label: t('resume.openEdit'),
      iconClass: 'fa-regular fa-pen-to-square',
      onClick: () => onEdit(resumeId),
    },
    ...(onAnalyzeWithAI
      ? [
          {
            key: 'analyze',
            label: t('resume.analyzeWithAI'),
            iconClass: 'fa-solid fa-wand-magic-sparkles',
            onClick: () => onAnalyzeWithAI(resumeId),
          },
        ]
      : []),
    {
      key: 'dup',
      label: duplicateLoadingId === resumeId ? t('resume.duplicating') : t('resume.duplicate'),
      iconClass: duplicateLoadingId === resumeId ? 'fa-solid fa-circle-notch' : 'fa-regular fa-copy',
      onClick: () => {
        if (duplicateLoadingId === resumeId) return;
        onDuplicate(resumeId);
      },
    },
    {
      key: 'pdf',
      label: downloadLoadingId === resumeId ? t('resume.generatingPdf') : t('resume.exportPdf'),
      iconClass: downloadLoadingId === resumeId ? 'fa-solid fa-circle-notch' : 'fa-regular fa-file-pdf',
      onClick: () => {
        if (downloadLoadingId === resumeId) return;
        onExport(resumeId);
      },
    },
    {
      key: 'del',
      label: t('resume.delete'),
      iconClass: 'fa-regular fa-trash-can',
      danger: true,
      onClick: () => onDelete(resumeId),
    },
  ];

  return items;
}
