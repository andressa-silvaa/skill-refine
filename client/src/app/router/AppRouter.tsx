import { Navigate, Route, Routes } from 'react-router-dom';

import { LoginPage } from '@/pages/auth/login';
import { ConfirmEmailPage } from '@/pages/auth/confirm-email';
import { OAuthCallbackPage } from '@/pages/auth/oauth-callback';
import { RegisterPage } from '@/pages/auth/register';
import { ResetCodePage, ResetEmailPage, ResetNewPasswordPage, ResetSuccessPage } from '@/pages/auth/reset-password';
import { VerifyEmailPage } from '@/pages/auth/verify-email';
import { ProtectedPage } from '@/pages/protected';

import { RequireAuth } from './RequireAuth';

export function AppRouter() {
  return (
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

      <Route
        path="/protected"
        element={
          <RequireAuth>
            <ProtectedPage />
          </RequireAuth>
        }
      />

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}


