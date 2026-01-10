import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { sessionApi } from '../api/sessionApi';
import { getHasRefreshCookieHint } from '../lib/refreshFlag';
import type { SessionPreferences, SessionStatus, SessionUser } from './types';
import { profileApi } from '../api/profileApi';
import { applyAppearancePreferences } from '@/shared/lib/theme/appearance';
import { i18n } from '@/shared/lib/i18n';
import { applyLanguagePreferences } from '@/shared/lib/language/applyLanguagePreferences';
import { normalizePreferences } from './preferences';

type SessionState = {
  status: SessionStatus;
  user: SessionUser | null;
  preferences: SessionPreferences | null;
};

type SessionActions = {
  bootstrap: (options?: { force?: boolean }) => Promise<void>;
  login: (payload: { email: string; password: string }) => Promise<void>;
  loginGoogle: (payload: { credential: string }) => Promise<void>;
  register: (payload: { email: string; full_name: string; birth_date?: string | null; password: string }) => Promise<{
    user: SessionUser;
    email_confirmation_sent?: boolean;
  }>;
  logout: () => Promise<void>;
  updateUser: (patch: Partial<SessionUser>) => void;
  updatePreferences: (patch: Partial<SessionPreferences>) => void;
};

const SessionContext = createContext<{ state: SessionState; actions: SessionActions } | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: 'unknown', user: null, preferences: null });

  const loadPreferences = useCallback(() => {
    return profileApi
      .getPreferences()
      .then((prefs) => {
        const next = normalizePreferences(prefs);
        setState((prev) => ({ ...prev, preferences: next }));
        applyAppearancePreferences({ theme: next.theme, accent_color: next.accent_color });
        applyLanguagePreferences({ language: next.language });
        void i18n.changeLanguage(next.language);
      })
      .catch(() => void 0);
  }, []);

  const bootstrap = useCallback(async (options?: { force?: boolean }) => {
    if (!options?.force && !getHasRefreshCookieHint()) {
      setState({ status: 'anonymous', user: null, preferences: null });
      return;
    }
    try {
      await sessionApi.refresh();
      const user = await sessionApi.me();
      setState((prev) => ({ ...prev, status: 'authenticated', user }));
      void loadPreferences();
    } catch (e) {
      setState({ status: 'anonymous', user: null, preferences: null });
    }
  }, [loadPreferences]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(async (payload: { email: string; password: string }) => {
    const user = await sessionApi.login(payload);
    setState((prev) => ({ ...prev, status: 'authenticated', user }));
    void loadPreferences();
  }, [loadPreferences]);

  const loginGoogle = useCallback(async (payload: { credential: string }) => {
    const user = await sessionApi.loginGoogle(payload);
    setState((prev) => ({ ...prev, status: 'authenticated', user }));
    void loadPreferences();
  }, [loadPreferences]);

  const register = useCallback(
    async (payload: { email: string; full_name: string; birth_date?: string | null; password: string }) => {
      return sessionApi.register(payload);
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      await sessionApi.logout();
    } finally {
      // Garante saída mesmo se o request falhar (UX previsível)
      setState({ status: 'anonymous', user: null, preferences: null });
      applyAppearancePreferences({ theme: 'light', accent_color: 'pink' });
      applyLanguagePreferences({ language: 'pt-BR' });
      void i18n.changeLanguage('pt-BR');
    }
  }, []);

  const updateUser = useCallback((patch: Partial<SessionUser>) => {
    setState((prev) => {
      if (!prev.user) return prev;
      return { ...prev, user: { ...prev.user, ...patch } };
    });
  }, []);

  const updatePreferences = useCallback((patch: Partial<SessionPreferences>) => {
    setState((prev) => {
      if (!prev.preferences) return prev;
      return { ...prev, preferences: { ...prev.preferences, ...patch } };
    });
  }, []);

  const actions: SessionActions = useMemo(
    () => ({ bootstrap, login, loginGoogle, register, logout, updateUser, updatePreferences }),
    [bootstrap, login, loginGoogle, register, logout, updateUser, updatePreferences]
  );

  return <SessionContext.Provider value={{ state, actions }}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used within SessionProvider');
  return ctx.state;
}

export function useSessionActions() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSessionActions must be used within SessionProvider');
  return ctx.actions;
}


