import type { ResumeViewModel } from '@/entities/resume';
import { Badge, DropdownMenu, IconButton, Tooltip } from '@/shared/ui';
import { useIsTruncated } from '@/shared/lib/hooks/useIsTruncated';

import './ResumesList.css';

type Props = {
  items: ResumeViewModel[];
  onEdit: (id: string) => void;
  onDuplicate: (id: string) => void;
  onExport: (id: string) => void;
  onDelete: (id: string) => void;
};

function ResumeNameButton({ name, onClick }: { name: string; onClick: () => void }) {
  const { ref, isTruncated } = useIsTruncated<HTMLButtonElement>();

  return (
    <Tooltip content={name} show={isTruncated} align="top">
      <button ref={ref} type="button" className="sr-resumes-list__name" onClick={onClick}>
        {name}
      </button>
    </Tooltip>
  );
}

function TruncatedText({ text, className }: { text: string; className?: string }) {
  const { ref, isTruncated } = useIsTruncated<HTMLDivElement>();

  return (
    <Tooltip content={text} show={isTruncated} align="top">
      <div ref={ref} className={className}>
        {text}
      </div>
    </Tooltip>
  );
}

function TruncatedBadge({ children, tone }: { children: React.ReactNode; tone?: 'neutral' | 'success' | 'warning' }) {
  const { ref, isTruncated } = useIsTruncated<HTMLDivElement>();
  const text = typeof children === 'string' ? children : '';

  return (
    <Tooltip content={text} show={isTruncated} align="top">
      <div ref={ref} className="sr-resumes-list__badge-wrap">
        <Badge tone={tone}>{children}</Badge>
      </div>
    </Tooltip>
  );
}

function TruncatedSpan({ text }: { text: string }) {
  const { ref, isTruncated } = useIsTruncated<HTMLSpanElement>();

  return (
    <Tooltip content={text} show={isTruncated} align="top">
      <span ref={ref} className="sr-resumes-list__truncate">
        {text}
      </span>
    </Tooltip>
  );
}

export function ResumesList(props: Props) {
  const { items, onEdit, onDuplicate, onExport, onDelete } = props;

  return (
    <div className="sr-resumes-list" role="table" aria-label="Lista de currículos">
      <div className="sr-resumes-list__head" role="row">
        <div role="columnheader">Nome</div>
        <div role="columnheader">Status</div>
        <div className="sr-resumes-list__hide-sm" role="columnheader">
          Última atualização
        </div>
        <div role="columnheader">Score</div>
        {/* Mantém a coluna de ações SEMPRE existente para alinhar com as rows */}
        <div role="columnheader" className="sr-resumes-list__head-actions" aria-label="Ações" />
      </div>

      {items.map((vm) => (
        <div key={vm.id} className="sr-resumes-list__row" role="row">
          <ResumeNameButton name={vm.name} onClick={() => onEdit(vm.id)} />

          <div className="sr-resumes-list__cell">
            <TruncatedBadge tone={vm.statusTone}>{vm.statusLabel}</TruncatedBadge>
          </div>

          <TruncatedText
            text={vm.updatedAtLabel}
            className="sr-resumes-list__hide-sm sr-resumes-list__muted sr-resumes-list__truncate"
          />

          <div className="sr-resumes-list__score">
            <i className="fa-solid fa-star" aria-hidden />
            <TruncatedSpan text={vm.scoreLabel} />
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
