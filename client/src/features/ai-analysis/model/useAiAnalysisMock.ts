import { useCallback, useMemo, useState } from 'react';

import { useResumes } from '@/features/resume';

import type {
  AnalysisResult,
  AnalysisStatus,
  ImprovementInsightItem,
  InsightItem,
  ResumeOption,
} from './types';

const MOCK_DELAY_MS = 1000;

const MOCK_RESULTS: AnalysisResult[] = [
  {
    score: 85,
    scoreLabel: 'Muito bom',
    ats: 92,
    atsBadge: 'excellent',
    clarity: 78,
    clarityBadge: 'good',
    seniorityLabel: 'Pleno/Sênior',
    strengths: [
      { key: 'analysis.insights.strengths.relevant_experience', params: {} },
      { key: 'analysis.insights.strengths.education_aligned', params: {} },
      { key: 'analysis.insights.strengths.professional_summary', params: {} },
    ] as InsightItem[],
    improvements: [
      { key: 'analysis.insights.improvements.add_metrics', priority: 'high', params: { section: 'experience' } },
      { key: 'analysis.insights.improvements.ats_keywords', priority: 'medium', params: {} },
      { key: 'analysis.insights.improvements.action_verbs', priority: 'medium', params: {} },
    ] as ImprovementInsightItem[],
  },
  {
    score: 72,
    scoreLabel: 'Bom',
    ats: 68,
    atsBadge: 'good',
    clarity: 88,
    clarityBadge: 'excellent',
    seniorityLabel: 'Pleno',
    strengths: [
      { key: 'analysis.insights.strengths.clear_structure', params: {} },
      { key: 'analysis.insights.strengths.education_aligned', params: {} },
      { key: 'analysis.insights.strengths.relevant_experience', params: {} },
    ] as InsightItem[],
    improvements: [
      { key: 'analysis.insights.improvements.ats_keywords', priority: 'high', params: {} },
      { key: 'analysis.insights.improvements.executive_summary', priority: 'medium', params: {} },
      { key: 'analysis.insights.improvements.add_metrics', priority: 'low', params: {} },
    ] as ImprovementInsightItem[],
  },
  {
    score: 90,
    scoreLabel: 'Excelente',
    ats: 95,
    atsBadge: 'excellent',
    clarity: 82,
    clarityBadge: 'excellent',
    seniorityLabel: 'Sênior',
    strengths: [
      { key: 'analysis.insights.strengths.ats_keywords', params: {} },
      { key: 'analysis.insights.strengths.relevant_experience', params: {} },
      { key: 'analysis.insights.strengths.clear_structure', params: {} },
    ] as InsightItem[],
    improvements: [
      { key: 'analysis.insights.improvements.clarity_conciseness', priority: 'low', params: {} },
      { key: 'analysis.insights.improvements.relevant_links', priority: 'low', params: {} },
    ] as ImprovementInsightItem[],
  },
];

export function useAiAnalysisMock() {
  const resumes = useResumes();
  const [selectedResumeId, setSelectedResumeId] = useState('');
  const [status, setStatus] = useState<AnalysisStatus>('idle');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [mockVariant, setMockVariant] = useState(0);

  const resumeOptions: ResumeOption[] = useMemo(() => {
    return resumes.viewModels.map((vm) => ({
      value: vm.id,
      label: vm.name?.trim() || vm.id,
    }));
  }, [resumes.viewModels]);

  const runAnalysis = useCallback(() => {
    if (!selectedResumeId) return;
    setStatus('loading');
    setResult(null);
    const variant = mockVariant % MOCK_RESULTS.length;
    const resultToSet: AnalysisResult = MOCK_RESULTS[variant]!;
    setTimeout(() => {
      setResult(resultToSet);
      setStatus('success');
      setMockVariant((v) => v + 1);
    }, MOCK_DELAY_MS + Math.random() * 300);
  }, [selectedResumeId, mockVariant]);

  const retry = useCallback(() => {
    setStatus('idle');
    setResult(null);
  }, []);

  const simulateError = useCallback(() => {
    setStatus('loading');
    setResult(null);
    setTimeout(() => setStatus('error'), MOCK_DELAY_MS);
  }, []);

  return {
    resumeOptions,
    selectedResumeId,
    setSelectedResumeId,
    status,
    result,
    runAnalysis,
    retry,
    simulateError,
  };
}
