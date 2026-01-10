import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { sessionApi } from '../api/sessionApi';
import { getHasRefreshCookieHint } from '../lib/refreshFlag';
import type { SessionStatus, SessionUser } from './types';
import { profileApi } from '../api/profileApi';
import { applyAppearancePreferences } from '@/shared/lib/theme/appearance';

type SessionState = {
  status: SessionStatus;
  user: SessionUser | null;
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
};

const SessionContext = createContext<{ state: SessionState; actions: SessionActions } | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: 'unknown', user: null });

  const bootstrap = useCallback(async (options?: { force?: boolean }) => {
    if (!options?.force && !getHasRefreshCookieHint()) {
      setState({ status: 'anonymous', user: null });
      return;
    }
    try {
      await sessionApi.refresh();
      const user = await sessionApi.me();
      setState({ status: 'authenticated', user });
      void profileApi
        .getPreferences()
        .then((prefs) => {
          applyAppearancePreferences({
            theme: (prefs.theme as any) ?? null,
            accent_color: (prefs.accent_color ?? prefs.accentColor ?? null) as any,
          });
        })
        .catch(() => void 0);
    } catch (e) {
      setState({ status: 'anonymous', user: null });
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(async (payload: { email: string; password: string }) => {
    const user = await sessionApi.login(payload);
    setState({ status: 'authenticated', user });
    void profileApi
      .getPreferences()
      .then((prefs) => {
        applyAppearancePreferences({
          theme: (prefs.theme as any) ?? null,
          accent_color: (prefs.accent_color ?? prefs.accentColor ?? null) as any,
        });
      })
      .catch(() => void 0);
  }, []);

  const loginGoogle = useCallback(async (payload: { credential: string }) => {
    const user = await sessionApi.loginGoogle(payload);
    setState({ status: 'authenticated', user });
    void profileApi
      .getPreferences()
      .then((prefs) => {
        applyAppearancePreferences({
          theme: (prefs.theme as any) ?? null,
          accent_color: (prefs.accent_color ?? prefs.accentColor ?? null) as any,
        });
      })
      .catch(() => void 0);
  }, []);

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
      setState({ status: 'anonymous', user: null });
      applyAppearancePreferences({ theme: 'light', accent_color: 'pink' });
    }
  }, []);

  const updateUser = useCallback((patch: Partial<SessionUser>) => {
    setState((prev) => {
      if (!prev.user) return prev;
      return { ...prev, user: { ...prev.user, ...patch } };
    });
  }, []);

  const actions: SessionActions = useMemo(
    () => ({ bootstrap, login, loginGoogle, register, logout, updateUser }),
    [bootstrap, login, loginGoogle, register, logout, updateUser]
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


