import { apiRequest } from '@/shared/api';

import type { DashboardSummaryResponse } from '../model/types';

export const dashboardApi = {
  summary() {
    return apiRequest<DashboardSummaryResponse>('/dashboard/summary');
  },
};

