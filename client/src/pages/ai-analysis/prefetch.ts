/**
 * Warms the same lazy chunk as {@link AppRouter}'s AiAnalysisPage route so navigation
 * from currículos does not wait on the network for the JS bundle.
 */
export function prefetchAiAnalysisRoute(): void {
  void import('@/pages/ai-analysis');
}
