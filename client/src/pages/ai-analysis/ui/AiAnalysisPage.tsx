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

          <section className="sr-ai-analysis__content">
            {isLoading && <AnalysisSkeleton />}

            {isEmpty && !isLoading && <AnalysisEmptyState />}

            {isError && <AnalysisErrorState onRetry={retry} />}

            {isSuccess && result && (
              <>
                <MetricsGrid result={result} />
                <InsightList result={result} selectedResumeId={selectedResumeId} />
              </>
            )}
          </section>
        </div>
      </main>
    </AppShell>
  );
}
