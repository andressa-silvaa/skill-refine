import { useState } from 'react';

import { useResumesMock } from '@/features/resume';
import { notify } from '@/shared/lib/notify';
import {
  ConfirmDeleteResumeModal,
  ResumesEmpty,
  ResumesGrid,
  ResumesHeader,
  ResumesList,
  ResumesSkeleton,
  ResumesToolbar,
} from '@/widgets/resumes';
import { ResumeBuilderWizard } from '@/widgets/resume-builder';
import { AppShell } from '@/widgets/app-shell';

import '@/shared/ui/sr-controls/SrControls.css';
import './ResumesPage.css';

export function ResumesPage() {
  const resumes = useResumesMock();
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [newOpen, setNewOpen] = useState(false);

  const openFilters = () => notify.info('Filtros em breve.');
  const onEdit = (id: string) => notify.info(`Abrir currículo ${id} (mock).`);

  const onDuplicate = (id: string) => {
    resumes.duplicate(id);
    notify.success('Currículo duplicado (mock).');
  };

  const onExport = () => notify.success('Solicitação de exportação enviada.');

  const onDelete = (id: string) => setDeleteId(id);
  const closeDelete = () => setDeleteId(null);

  const confirmDelete = () => {
    if (!deleteId) return;
    resumes.remove(deleteId);
    setDeleteId(null);
    notify.success('Currículo excluído (mock).');
  };

  return (
    <AppShell>
      <main className="sr-resumes" aria-label="Currículos">
        <ResumesHeader onCreate={() => setNewOpen(true)} />

        <ResumesToolbar
          query={resumes.query}
          onQueryChange={resumes.setQuery}
          view={resumes.view}
          onViewChange={resumes.setView}
          sort={resumes.sort}
          onSortChange={resumes.setSort}
          onOpenFilters={openFilters}
        />

        <section className="sr-resumes__content">
          {resumes.loading ? (
            <ResumesSkeleton view={resumes.view} />
          ) : resumes.viewModels.length === 0 ? (
            <ResumesEmpty onCreate={() => setNewOpen(true)} />
          ) : resumes.view === 'grid' ? (
            <ResumesGrid
              items={resumes.viewModels}
              onEdit={onEdit}
              onDuplicate={onDuplicate}
              onExport={onExport}
              onDelete={onDelete}
            />
          ) : (
            <ResumesList
              items={resumes.viewModels}
              onEdit={onEdit}
              onDuplicate={onDuplicate}
              onExport={onExport}
              onDelete={onDelete}
            />
          )}
        </section>

        <ResumeBuilderWizard
          open={newOpen}
          onClose={() => setNewOpen(false)}
          onCreate={(data) => {
            resumes.create(data);
            notify.success('Currículo criado (mock).');
          }}
        />

        <ConfirmDeleteResumeModal open={Boolean(deleteId)} onClose={closeDelete} onConfirm={confirmDelete} />
      </main>
    </AppShell>
  );
}
