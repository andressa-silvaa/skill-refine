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
};

export function ResumesGrid(props: Props) {
  const { items, onEdit, onDuplicate, onExport, onDelete } = props;

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
                <IconButton aria-label="Ações">
                  <i className="fa-solid fa-ellipsis-vertical" aria-hidden />
                </IconButton>
              }
              items={[
                { key: 'edit', label: 'Abrir/Editar', iconClass: 'fa-regular fa-pen-to-square', onClick: () => onEdit(vm.id) },
                { key: 'dup', label: 'Duplicar', iconClass: 'fa-regular fa-copy', onClick: () => onDuplicate(vm.id) },
                { key: 'pdf', label: 'Exportar PDF', iconClass: 'fa-regular fa-file-pdf', onClick: () => onExport(vm.id) },
                { key: 'del', label: 'Excluir', iconClass: 'fa-regular fa-trash-can', danger: true, onClick: () => onDelete(vm.id) },
              ]}
            />
          </div>

          <ResumeMeta vm={vm} />
        </Card>
      ))}
    </div>
  );
}
