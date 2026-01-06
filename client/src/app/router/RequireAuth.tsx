import { Navigate } from 'react-router-dom';
import type { ReactElement } from 'react';

import { useSession } from '@/entities/session';

export function RequireAuth({ children }: { children: ReactElement }) {
  const { status } = useSession();

  if (status === 'unknown') return null;
  if (status === 'anonymous') return <Navigate to="/login" replace />;

  return children;
}


