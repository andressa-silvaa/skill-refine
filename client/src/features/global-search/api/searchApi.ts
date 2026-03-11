import { apiRequest } from '@/shared/api/http';

export type SearchResultItem = {
  type: 'resume' | 'analysis' | 'version';
  id: string;
  title: string;
  subtitle: string;
  url: string;
};

export type SearchResponse = {
  items: SearchResultItem[];
};

export const searchApi = {
  search(params: { q: string; types?: string[]; limit?: number }, signal?: AbortSignal) {
    const searchParams = new URLSearchParams();
    searchParams.set('q', params.q.trim());
    if (params.types?.length) searchParams.set('types', params.types.join(','));
    if (params.limit != null) searchParams.set('limit', String(params.limit));
    return apiRequest<SearchResponse>(`/search/?${searchParams.toString()}`, { signal });
  },
};
