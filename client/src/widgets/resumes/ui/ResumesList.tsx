import type { ResumeViewModel } from '@/entities/resume';
import { Badge, DropdownMenu, IconButton } from '@/shared/ui';

import './ResumesList.css';

type Props = {
  items: ResumeViewModel[];
  onEdit: (id: string) => void;
  onDuplicate: (id: string) => void;
  onExport: (id: string) => void;
  onDelete: (id: string) => void;
};

export function ResumesList(props: Props) {
  const { items, onEdit, onDuplicate, onExport, onDelete } = props;

  return (
    <div className="sr-resumes-list">
      <div className="sr-resumes-list__head" role="row">
        <div role="columnheader">Nome</div>
        <div role="columnheader">Status</div>
        <div className="sr-resumes-list__hide-sm" role="columnheader">
          Última atualização
        </div>
        <div role="columnheader">Score</div>
        <div role="columnheader" aria-label="Ações" />
      </div>

      {items.map((vm) => (
        <div key={vm.id} className="sr-resumes-list__row" role="row">
          <button type="button" className="sr-resumes-list__name" onClick={() => onEdit(vm.id)}>
            {vm.name}
          </button>
          <div>
            <Badge tone={vm.statusTone}>{vm.statusLabel}</Badge>
          </div>
          <div className="sr-resumes-list__hide-sm sr-resumes-list__muted">{vm.updatedAtLabel}</div>
          <div className="sr-resumes-list__score">
            <i className="fa-solid fa-star" aria-hidden />
            <span>{vm.scoreLabel}</span>
          </div>
          <div className="sr-resumes-list__actions">
            <IconButton aria-label="Editar" onClick={() => onEdit(vm.id)}>
              <i className="fa-regular fa-pen-to-square" aria-hidden />
            </IconButton>
            <DropdownMenu
              trigger={
                <IconButton aria-label="Mais ações">
                  <i className="fa-solid fa-ellipsis-vertical" aria-hidden />
                </IconButton>
              }
              items={[
                { key: 'dup', label: 'Duplicar', iconClass: 'fa-regular fa-copy', onClick: () => onDuplicate(vm.id) },
                { key: 'pdf', label: 'Exportar PDF', iconClass: 'fa-regular fa-file-pdf', onClick: () => onExport(vm.id) },
                { key: 'del', label: 'Excluir', iconClass: 'fa-regular fa-trash-can', danger: true, onClick: () => onDelete(vm.id) },
              ]}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
