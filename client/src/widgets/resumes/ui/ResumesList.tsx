import { useTranslation } from 'react-i18next';

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
  duplicateLoadingId?: string | null;
  downloadLoadingId?: string | null;
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
  const { items, onEdit, onDuplicate, onExport, onDelete, duplicateLoadingId, downloadLoadingId } = props;
  const { t } = useTranslation();

  return (
    <div className="sr-resumes-list" role="table" aria-label={t('resume.mainAria')}>
      <div className="sr-resumes-list__head" role="row">
        <div role="columnheader">{t('resume.sortName')}</div>
        <div role="columnheader">{t('profile.accountStatus')}</div>
        <div className="sr-resumes-list__hide-sm" role="columnheader">
          {t('resume.listLastUpdate')}
        </div>
        <div role="columnheader">{t('resume.listScore')}</div>
        <div role="columnheader" className="sr-resumes-list__head-actions" aria-label={t('resume.actions')} />
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
            <IconButton aria-label={t('resume.openEdit')} onClick={() => onEdit(vm.id)}>
              <i className="fa-regular fa-pen-to-square" aria-hidden />
            </IconButton>

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
        </div>
      ))}
    </div>
  );
}
