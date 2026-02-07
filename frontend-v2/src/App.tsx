import { useState, useEffect } from 'react';
import LoginPage from './pages/LoginPage';
import ChatPage from './pages/ChatPage';
import './App.css';

function App() {
  // URL 해시(#chat)로 로그인 상태 관리
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    return window.location.hash === '#chat';
  });
  const [memberId, setMemberId] = useState('guest');

  // 해시 변경 감지
  useEffect(() => {
    const handleHashChange = () => {
      setIsLoggedIn(window.location.hash === '#chat');
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleLogin = () => {
    window.location.hash = '#chat';
    setMemberId('guest');
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    window.location.hash = '';
    setMemberId('');
    setIsLoggedIn(false);
  };

  return (
    <div className="app-container">
      {isLoggedIn ? (
        <ChatPage onLogout={handleLogout} memberId={memberId} />
      ) : (
        <LoginPage onLogin={handleLogin} />
      )}
    </div>
  );
}

export default App;
