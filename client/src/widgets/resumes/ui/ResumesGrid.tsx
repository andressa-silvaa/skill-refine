import { memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import type { ResumeViewModel } from '@/entities/resume';
import type { LatestAnalysisInfo } from '@/features/ai-analysis';
import { Card, DropdownMenu, IconButton } from '@/shared/ui';

import { ResumeMeta } from './ResumeMeta';
import { ResumeThumb } from './ResumeThumb';
import { buildResumeActionsMenu } from '../model/buildResumeActionsMenu';

import './ResumesGrid.css';

type GridCardProps = {
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

const ResumeGridCard = memo(function ResumeGridCard(props: GridCardProps) {
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
  }, [
    vm.id,
    duplicateLoadingId,
    downloadLoadingId,
    onEdit,
    onDuplicate,
    onExport,
    onDelete,
    onAnalyzeWithAI,
    onActionsMenuOpen,
    t,
  ]);

  return (
    <Card className="sr-resumes-grid__card" role="listitem">
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
          items={menuItems}
          onOpenChange={onActionsMenuOpen}
        />
      </div>

      <ResumeMeta vm={vm} analysisInfo={analysisInfo} />
    </Card>
  );
});

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
  analysisByResumeId?: Map<string, import('@/features/ai-analysis').LatestAnalysisInfo>;
};

export function ResumesGrid(props: Props) {
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

  return (
    <div className="sr-resumes-grid" role="list">
      {items.map((vm) => (
        <ResumeGridCard
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
