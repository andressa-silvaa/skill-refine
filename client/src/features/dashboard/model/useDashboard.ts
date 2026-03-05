import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useSession } from '@/entities/session';

import { dashboardApi } from '../api/dashboardApi';
import { mapDashboardResponseToViewModel } from './mappers';
import type { DashboardData } from './viewTypes';

type UseDashboardState = {
  data: DashboardData | null;
  loading: boolean;
  error: unknown | null;
};

function firstNameFromUserFullName(fullName: string | null | undefined, fallback: string): string {
  const raw = (fullName || '').trim();
  if (!raw) return fallback;
  return raw.split(/\s+/)[0] || fallback;
}

export function useDashboard() {
  const { t, i18n } = useTranslation();
  const session = useSession();

  const [state, setState] = useState<UseDashboardState>({
    data: null,
    loading: true,
    error: null,
  });

  const reload = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response = await dashboardApi.summary();
      const userName = firstNameFromUserFullName(session.user?.full_name, t('dashboard.userFallbackName'));
      const data = mapDashboardResponseToViewModel(response, {
        locale: i18n.language || 'pt-BR',
        userName,
        t,
      });
      setState({ data, loading: false, error: null });
    } catch (error) {
      setState((prev) => ({ ...prev, loading: false, error }));
      throw error;
    }
  }, [i18n.language, session.user?.full_name, t]);

  useEffect(() => {
    void reload().catch(() => null);
  }, [reload]);

  return {
    data: state.data,
    loading: state.loading,
    error: state.error,
    reload,
  };
}

