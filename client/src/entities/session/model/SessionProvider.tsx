import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { sessionApi } from '../api/sessionApi';
import { getHasRefreshCookieHint } from '../lib/refreshFlag';
import type { SessionStatus, SessionUser } from './types';

type SessionState = {
  status: SessionStatus;
  user: SessionUser | null;
};

type SessionActions = {
  bootstrap: () => Promise<void>;
  login: (payload: { email: string; password: string }) => Promise<void>;
  loginGoogle: (payload: { credential: string }) => Promise<void>;
  register: (payload: { email: string; full_name: string; birth_date?: string | null; password: string }) => Promise<{
    user: SessionUser;
    email_confirmation_sent?: boolean;
  }>;
  logout: () => Promise<void>;
};

const SessionContext = createContext<{ state: SessionState; actions: SessionActions } | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: 'unknown', user: null });

  const bootstrap = useCallback(async () => {
    // Avoid hitting /refresh on first load when we know there's no previous session.
    // This prevents noisy 401s in the console on the public login screen.
    if (!getHasRefreshCookieHint()) {
      setState({ status: 'anonymous', user: null });
      return;
    }
    try {
      await sessionApi.refresh();
      const user = await sessionApi.me();
      setState({ status: 'authenticated', user });
    } catch (e) {
      // If there is no refresh cookie, treat as anonymous.
      setState({ status: 'anonymous', user: null });
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(async (payload: { email: string; password: string }) => {
    const user = await sessionApi.login(payload);
    setState({ status: 'authenticated', user });
  }, []);

  const loginGoogle = useCallback(async (payload: { credential: string }) => {
    const user = await sessionApi.loginGoogle(payload);
    setState({ status: 'authenticated', user });
  }, []);

  const register = useCallback(
    async (payload: { email: string; full_name: string; birth_date?: string | null; password: string }) => {
      return sessionApi.register(payload);
      // After register, require explicit login (clean + avoids auto-session on register).
    },
    []
  );

  const logout = useCallback(async () => {
    await sessionApi.logout();
    setState({ status: 'anonymous', user: null });
  }, []);

  const actions: SessionActions = useMemo(
    () => ({ bootstrap, login, loginGoogle, register, logout }),
    [bootstrap, login, loginGoogle, register, logout]
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


