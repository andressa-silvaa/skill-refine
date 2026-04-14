import { memo, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import type { ResumeViewModel } from '@/entities/resume';
import type { LatestAnalysisInfo } from '@/features/ai-analysis';
import { Badge, DropdownMenu, IconButton, Tooltip } from '@/shared/ui';
import { useIsTruncated } from '@/shared/lib/hooks/useIsTruncated';
import { buildResumeActionsMenu } from '../model/buildResumeActionsMenu';

import './ResumesList.css';

type Props = {
  items: ResumeViewModel[];
  onEdit: (id: string) => void;
  onDuplicate: (id: string) => void;
  onExport: (id: string) => void;
  onDelete: (id: string) => void;
  onAnalyzeWithAI?: (id: string) => void;
  onActionsMenuOpen?: (open: boolean) => void;
  duplicateLoadingId?: string | null;
  downloadLoadingId?: string | null;
  analysisByResumeId?: Map<string, LatestAnalysisInfo>;
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

type ListItemProps = {
  vm: ResumeViewModel;
  onEdit: (id: string) => void;
  onDuplicate: (id: string) => void;
  onExport: (id: string) => void;
  onDelete: (id: string) => void;
  onAnalyzeWithAI?: (id: string) => void;
  onActionsMenuOpen?: (open: boolean) => void;
  duplicateLoadingId?: string | null;
  downloadLoadingId?: string | null;
  analysisInfo?: LatestAnalysisInfo | null;
};

const ResumesListItem = memo(function ResumesListItem(props: ListItemProps) {
  const {
    vm,
    onEdit,
    onDuplicate,
    onExport,
    onDelete,
    onAnalyzeWithAI,
    onActionsMenuOpen,
    duplicateLoadingId,
    downloadLoadingId,
    analysisInfo,
  } = props;
  const { t } = useTranslation();

  const handleNameClick = useCallback(() => onEdit(vm.id), [vm.id, onEdit]);
  const handleEditClick = useCallback(() => onEdit(vm.id), [vm.id, onEdit]);

  const isAnalyzing = analysisInfo?.status === 'pending' || analysisInfo?.status === 'running';
  const aiScoreLabel =
    analysisInfo?.status === 'done' && analysisInfo.score != null
      ? t('analysis.cardScore', { score: analysisInfo.score })
      : null;

  const menuItems = useMemo(() => {
    return buildResumeActionsMenu({
      resumeId: vm.id,
      duplicateLoadingId,
      downloadLoadingId,
      onEdit,
      onDuplicate,
      onExport,
      onDelete,
      onAnalyzeWithAI,
      t,
    });
  }, [vm.id, duplicateLoadingId, downloadLoadingId, onEdit, onDuplicate, onExport, onDelete, onAnalyzeWithAI, t]);

  return (
    <div className="sr-resumes-list__row" role="row">
      <ResumeNameButton name={vm.name} onClick={handleNameClick} />

      <div className="sr-resumes-list__cell">
        <TruncatedBadge tone={vm.statusTone}>{vm.statusLabel}</TruncatedBadge>
      </div>

      <TruncatedText
        text={vm.updatedAtLabel}
        className="sr-resumes-list__hide-sm sr-resumes-list__muted sr-resumes-list__truncate"
      />

      <div className="sr-resumes-list__score">
        {isAnalyzing ? (
          <TruncatedSpan text={t('analysis.status.running')} />
        ) : aiScoreLabel ? (
          <TruncatedSpan text={aiScoreLabel} />
        ) : (
          <>
            <i className="fa-solid fa-star" aria-hidden />
            <TruncatedSpan text={vm.scoreLabel} />
          </>
        )}
      </div>

      <div className="sr-resumes-list__actions">
        <IconButton aria-label={t('resume.openEdit')} onClick={handleEditClick}>
          <i className="fa-regular fa-pen-to-square" aria-hidden />
        </IconButton>

        <DropdownMenu
          trigger={
            <IconButton aria-label={t('resume.actions')}>
              <i className="fa-solid fa-ellipsis-vertical" aria-hidden />
            </IconButton>
          }
          items={menuItems}
          onOpenChange={onActionsMenuOpen}
        />
      </div>
    </div>
  );
});

export function ResumesList(props: Props) {
  const {
    items,
    onEdit,
    onDuplicate,
    onExport,
    onDelete,
    onAnalyzeWithAI,
    onActionsMenuOpen,
    duplicateLoadingId,
    downloadLoadingId,
    analysisByResumeId,
  } = props;
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
        <ResumesListItem
          key={vm.id}
          vm={vm}
          onEdit={onEdit}
          onDuplicate={onDuplicate}
          onExport={onExport}
          onDelete={onDelete}
          onAnalyzeWithAI={onAnalyzeWithAI}
          onActionsMenuOpen={onActionsMenuOpen}
          duplicateLoadingId={duplicateLoadingId}
          downloadLoadingId={downloadLoadingId}
          analysisInfo={analysisByResumeId?.get(vm.id)}
        />
      ))}
    </div>
  );
}
