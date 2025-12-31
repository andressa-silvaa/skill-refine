import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';
import { useState } from 'react';
import LoginPage from './pages/Login/LoginPage';
import RegisterPage from './pages/Register/RegisterPage';

function App() {
  const [page, setPage] = useState('login');

  const goToRegister = () => setPage('register');
  const goToLogin = () => setPage('login');

  return (
    <div className="app-shell">
      {page === 'login' ? (
        <LoginPage onGoRegister={goToRegister} />
      ) : (
        <RegisterPage onGoLogin={goToLogin} />
      )}
    </div>
  );
}

export default App;
