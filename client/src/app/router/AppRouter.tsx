import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { PageLoader } from '@/shared/ui';

import { LoginPage } from '@/pages/auth/login';
import { ConfirmEmailPage } from '@/pages/auth/confirm-email';
import { OAuthCallbackPage } from '@/pages/auth/oauth-callback';
import { PrivacyPage } from '@/pages/public/privacy';
import { RegisterPage } from '@/pages/auth/register';
import { TermsPage } from '@/pages/public/terms';
import {
  ResetCodePage,
  ResetEmailPage,
  ResetNewPasswordPage,
  ResetSuccessPage,
} from '@/pages/auth/reset-password';
import { VerifyEmailPage } from '@/pages/auth/verify-email';

import { RequireAuth } from './RequireAuth';
import { RouteLoadErrorBoundary } from './RouteLoadErrorBoundary';
import { ProtectedAppLayout } from './ProtectedAppLayout';

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
  import('@/pages/resumes').then((m) => ({ default: m.ResumesPage }))
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
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/confirm-email" element={<ConfirmEmailPage />} />
        <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />

        <Route path="/reset/email" element={<ResetEmailPage />} />
        <Route path="/reset/code" element={<ResetCodePage />} />
        <Route path="/reset/new" element={<ResetNewPasswordPage />} />
        <Route path="/reset/success" element={<ResetSuccessPage />} />
        <Route
          path="/resume/print/:resumeId"
          element={
            <Suspense fallback={<PageLoader />}>
              <ResumePrintPage />
            </Suspense>
          }
        />

        <Route path="/protected" element={<RequireAuth><ProtectedAppLayout /></RequireAuth>}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="resumes" element={<ResumesPage />} />
          <Route path="ai-analysis" element={<AiAnalysisPage />} />
          <Route path="version-history" element={<VersionHistoryPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </RouteLoadErrorBoundary>
  );
}
