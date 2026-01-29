import { useTranslation } from 'react-i18next';

import type { ResumeViewModel } from '@/entities/resume';
import { Card, DropdownMenu, IconButton } from '@/shared/ui';

import { ResumeMeta } from './ResumeMeta';
import { ResumeThumb } from './ResumeThumb';

import './ResumesGrid.css';

type Props = {
  items: ResumeViewModel[];
  onEdit: (id: string) => void;
  onDuplicate: (id: string) => void;
  onExport: (id: string) => void;
  onDelete: (id: string) => void;
  duplicateLoadingId?: string | null;
  downloadLoadingId?: string | null;
};

export function ResumesGrid(props: Props) {
  const { items, onEdit, onDuplicate, onExport, onDelete, duplicateLoadingId, downloadLoadingId } = props;
  const { t } = useTranslation();

  return (
    <div className="sr-resumes-grid" role="list">
      {items.map((vm) => (
        <Card key={vm.id} className="sr-resumes-grid__card" role="listitem">
          <div className="sr-resumes-grid__header">
            <div className="sr-resumes-grid__title">
              <ResumeThumb />
              <div>
                <h3 className="sr-resumes-grid__name">{vm.name}</h3>
                <p className="sr-resumes-grid__updated">{vm.updatedAtLabel}</p>
              </div>
            </div>

            <DropdownMenu
              trigger={
                <IconButton aria-label={t('resume.actions')}>
                  <i className="fa-solid fa-ellipsis-vertical" aria-hidden />
                </IconButton>
              }
              items={[
                { key: 'edit', label: t('resume.openEdit'), iconClass: 'fa-regular fa-pen-to-square', onClick: () => onEdit(vm.id) },
                {
                  key: 'dup',
                  label: duplicateLoadingId === vm.id ? t('resume.duplicating') : t('resume.duplicate'),
                  iconClass: duplicateLoadingId === vm.id ? 'fa-solid fa-circle-notch' : 'fa-regular fa-copy',
                  onClick: () => {
                    if (duplicateLoadingId === vm.id) return;
                    onDuplicate(vm.id);
                  },
                },
                {
                  key: 'pdf',
                  label: downloadLoadingId === vm.id ? t('resume.generatingPdf') : t('resume.exportPdf'),
                  iconClass: downloadLoadingId === vm.id ? 'fa-solid fa-circle-notch' : 'fa-regular fa-file-pdf',
                  onClick: () => {
                    if (downloadLoadingId === vm.id) return;
                    onExport(vm.id);
                  },
                },
                { key: 'del', label: t('resume.delete'), iconClass: 'fa-regular fa-trash-can', danger: true, onClick: () => onDelete(vm.id) },
              ]}
            />
          </div>

          <ResumeMeta vm={vm} />
        </Card>
      ))}
    </div>
  );
}
