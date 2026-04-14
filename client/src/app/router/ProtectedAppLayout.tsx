import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';

import { RouteContentLoader } from '@/shared/ui';
import { AppShell } from '@/widgets/app-shell';

/**
 * Single persistent shell for all /protected/* routes so theme, sidebar state and animations
 * are not reset on every navigation (avoids flicker of default layout before preferences apply).
 */
export function ProtectedAppLayout() {
  return (
    <AppShell>
      <Suspense fallback={<RouteContentLoader />}>
        <Outlet />
      </Suspense>
    </AppShell>
  );
}
