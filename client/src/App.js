import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import LoginPage from './pages/Login/LoginPage';
import RegisterPage from './pages/Register/RegisterPage';
import ResetEmailPage from './pages/Recovery/ResetEmailPage';
import ResetCodePage from './pages/Recovery/ResetCodePage';
import ResetNewPasswordPage from './pages/Recovery/ResetNewPasswordPage';
import ResetSuccessPage from './pages/Recovery/ResetSuccessPage';

function AppRoutes() {
  const navigate = useNavigate();

  return (
    <Routes>
      <Route
        path="/login"
        element={<LoginPage onGoRegister={() => navigate('/register')} onGoForgot={() => navigate('/reset/email')} />}
      />

      <Route path="/register" element={<RegisterPage onGoLogin={() => navigate('/login')} />} />

      <Route
        path="/reset/email"
        element={
          <ResetEmailPage
            onBack={() => navigate(-1)}
            onContinue={() => navigate('/reset/code')}
            onGoLogin={() => navigate('/login')}
          />
        }
      />

      <Route
        path="/reset/code"
        element={
          <ResetCodePage
            onBack={() => navigate('/reset/email')}
            onConfirm={() => navigate('/reset/new')}
            onResend={() => {}}
            onGoLogin={() => navigate('/login')}
          />
        }
      />

      <Route
        path="/reset/new"
        element={
          <ResetNewPasswordPage
            onBack={() => navigate('/reset/code')}
            onSubmit={() => navigate('/reset/success')}
            onGoLogin={() => navigate('/login')}
          />
        }
      />

      <Route path="/reset/success" element={<ResetSuccessPage onGoLogin={() => navigate('/login')} />} />

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <div className="app-shell">
        <AppRoutes />
      </div>
    </Router>
  );
}

export default App;
