import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { PageLoader } from '@/shared/ui';

import { LoginPage } from '@/pages/auth/login';
import { ConfirmEmailPage } from '@/pages/auth/confirm-email';
import { OAuthCallbackPage } from '@/pages/auth/oauth-callback';
import { RegisterPage } from '@/pages/auth/register';
import {
  ResetCodePage,
  ResetEmailPage,
  ResetNewPasswordPage,
  ResetSuccessPage,
} from '@/pages/auth/reset-password';
import { VerifyEmailPage } from '@/pages/auth/verify-email';

import { RequireAuth } from './RequireAuth';
import { RouteLoadErrorBoundary } from './RouteLoadErrorBoundary';

const DashboardPage = lazy(() =>
  import('@/pages/dashboard').then((m) => ({ default: m.DashboardPage }))
);
const ProfilePage = lazy(() =>
  import('@/pages/profile').then((m) => ({ default: m.ProfilePage }))
);
const ResumePrintPage = lazy(() =>
  import('@/pages/resume-print').then((m) => ({ default: m.ResumePrintPage }))
);
const SettingsPage = lazy(() =>
  import('@/pages/settings').then((m) => ({ default: m.SettingsPage }))
);
const ResumesPage = lazy(() =>
  import('@/pages/curriculos').then((m) => ({ default: m.ResumesPage }))
);
const AiAnalysisPage = lazy(() =>
  import('@/pages/ai-analysis').then((m) => ({ default: m.AiAnalysisPage }))
);
const VersionHistoryPage = lazy(() =>
  import('@/pages/version-history').then((m) => ({ default: m.VersionHistoryPage }))
);

export function AppRouter() {
  return (
    <RouteLoadErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/confirm-email" element={<ConfirmEmailPage />} />
          <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />

          <Route path="/reset/email" element={<ResetEmailPage />} />
          <Route path="/reset/code" element={<ResetCodePage />} />
          <Route path="/reset/new" element={<ResetNewPasswordPage />} />
          <Route path="/reset/success" element={<ResetSuccessPage />} />
          <Route path="/resume/print/:resumeId" element={<ResumePrintPage />} />

          <Route
            path="/protected"
            element={
              <RequireAuth>
                <Navigate to="/protected/dashboard" replace />
              </RequireAuth>
            }
          />

          <Route
            path="/protected/dashboard"
            element={
              <RequireAuth>
                <DashboardPage />
              </RequireAuth>
            }
          />

          <Route
            path="/protected/profile"
            element={
              <RequireAuth>
                <ProfilePage />
              </RequireAuth>
            }
          />

          <Route
            path="/protected/settings"
            element={
              <RequireAuth>
                <SettingsPage />
              </RequireAuth>
            }
          />

          <Route
            path="/protected/resumes"
            element={
              <RequireAuth>
                <ResumesPage />
              </RequireAuth>
            }
          />

          <Route
            path="/protected/ai-analysis"
            element={
              <RequireAuth>
                <AiAnalysisPage />
              </RequireAuth>
            }
          />

          <Route
            path="/protected/version-history"
            element={
              <RequireAuth>
                <VersionHistoryPage />
              </RequireAuth>
            }
          />

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Suspense>
    </RouteLoadErrorBoundary>
  );
}
