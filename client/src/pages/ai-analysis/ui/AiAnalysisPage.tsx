import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { AppShell } from '@/widgets/app-shell';
import {
  useAiAnalysis,
  ResumeSelectCard,
  MetricsGrid,
  InsightList,
  AnalysisSkeleton,
  AnalysisErrorState,
  AnalysisEmptyState,
} from '@/features/ai-analysis';

import '@/shared/ui/sr-controls/SrControls.css';
import './AiAnalysisPage.css';

function formatLastAnalysisDate(iso: string): { dateStr: string; timeStr: string } | null {
  try {
    const d = new Date(iso);
    const dateStr = d.toLocaleDateString(undefined, { day: '2-digit', month: '2-digit', year: 'numeric' });
    const timeStr = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    return { dateStr, timeStr };
  } catch {
    return null;
  }
}

export function AiAnalysisPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const resumeIdFromQuery = searchParams.get('resumeId') ?? undefined;

  const {
    resumeOptions,
    selectedResumeId,
    setSelectedResumeId,
    status,
    result,
    runAnalysis,
    retry,
    lastAnalysisAt,
  } = useAiAnalysis(resumeIdFromQuery);

  const isEmpty = status === 'idle' && !result;
  const isLoading = status === 'loading';
  const isSuccess = status === 'success' && result;
  const isError = status === 'error';

  return (
    <AppShell>
      <main className="sr-ai-analysis" aria-label={t('analysis.mainAria')}>
        <div className="sr-ai-analysis__container">
          <header className="sr-ai-analysis__header">
            <div>
              <h1 className="sr-ai-analysis__h1">{t('analysis.title')}</h1>
              <p className="sr-ai-analysis__subtitle">{t('analysis.subtitle')}</p>
            </div>
          </header>

          <ResumeSelectCard
            options={resumeOptions}
            value={selectedResumeId}
            onChange={setSelectedResumeId}
            onAnalyze={runAnalysis}
            loading={isLoading}
            selectPlaceholder={t('analysis.selectPlaceholder')}
            analyzeButtonLabel={t('analysis.analyzeButton')}
          />

          {lastAnalysisAt && (() => {
            const formatted = formatLastAnalysisDate(lastAnalysisAt);
            const dateLabel = formatted
              ? `${formatted.dateStr} às ${formatted.timeStr}`
              : lastAnalysisAt;
            return (
              <p className="sr-ai-analysis__last" aria-live="polite">
                {t('analysis.lastAnalysis', { date: dateLabel })}
              </p>
            );
          })()}

          <section className="sr-ai-analysis__content">
            {isLoading && <AnalysisSkeleton />}

            {isEmpty && !isLoading && <AnalysisEmptyState />}

            {isError && <AnalysisErrorState onRetry={retry} />}

            {isSuccess && result && (
              <>
                <MetricsGrid result={result} />
                <InsightList result={result} />
              </>
            )}
          </section>
        </div>
      </main>
    </AppShell>
  );
}
