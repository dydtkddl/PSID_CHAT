import { useState } from 'react';
import './LoginPage.css';

interface LoginPageProps {
  onLogin: () => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!agreed) {
      setError('이용약관에 동의해주세요.');
      return;
    }

    setIsLoading(true);
    
    setTimeout(() => {
      onLogin();
      setIsLoading(false);
    }, 300);
  };

  return (
    <div className="login-page">
      {/* Decorative Background Elements */}
      <div className="login-bg-pattern"></div>
      
      {/* Left Panel - Brand Visual */}
      <div className="login-brand-panel">
        <div className="brand-content">
          <div className="brand-emblem">
            {/* KHU Lion Emblem - 호연지기 */}
            <svg viewBox="0 0 120 120" className="lion-emblem">
              {/* Outer circle */}
              <circle cx="60" cy="60" r="55" fill="none" stroke="currentColor" strokeWidth="1.5"/>
              {/* Lion face outline */}
              <ellipse cx="60" cy="65" rx="28" ry="30" fill="currentColor" opacity="0.15"/>
              {/* Mane */}
              <path d="M30 50 Q25 30 40 25 Q55 20 60 18 Q65 20 80 25 Q95 30 90 50" 
                    fill="none" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M25 60 Q20 45 30 35" fill="none" stroke="currentColor" strokeWidth="1"/>
              <path d="M95 60 Q100 45 90 35" fill="none" stroke="currentColor" strokeWidth="1"/>
              {/* Eyes */}
              <circle cx="48" cy="58" r="4" fill="currentColor" opacity="0.6"/>
              <circle cx="72" cy="58" r="4" fill="currentColor" opacity="0.6"/>
              {/* Nose */}
              <path d="M55 70 L60 75 L65 70 Z" fill="currentColor" opacity="0.5"/>
              {/* Mouth */}
              <path d="M50 82 Q60 90 70 82" fill="none" stroke="currentColor" strokeWidth="1.2"/>
            </svg>
          </div>
          <h2 className="brand-headline">
            학칙이 궁금할 땐
          </h2>
          <p className="brand-motto">
            경희대 규정 AI 어시스턴트
          </p>
          <div className="brand-divider"></div>
          <p className="brand-tagline">
            복잡한 학칙, 쉽고 빠르게 검색하세요
          </p>
        </div>
        
        {/* Decorative Lines */}
        <div className="brand-decoration">
          <div className="deco-line"></div>
          <div className="deco-line"></div>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="login-form-panel">
        <div className="login-container">
          {/* Logo Section */}
          <div className="login-logo-section">
            <img
              src="/asset/kyunghee.png"
              alt="Kyung Hee University"
              className="login-logo"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            <h1 className="login-title">경희대학교 규정 검색</h1>
            <p className="login-subtitle">
              학칙 및 시행세칙 검색 어시스턴트
            </p>
          </div>

          {/* Login Card */}
          <div className="login-card">
            <form onSubmit={handleSubmit}>
              {/* About Section */}
              <div className="about-section">
                <div className="about-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 16v-4M12 8h.01"/>
                  </svg>
                </div>
              <div className="about-content">
                  <h3>서비스 안내</h3>
                  <ul>
                    <li>경희대학교 공식 규정 기반</li>
                    <li>학칙, 시행세칙, 학사제도 지원</li>
                    <li>대화 내용은 연구 목적으로 기록될 수 있습니다</li>
                  </ul>
                </div>
              </div>

              {/* Terms Agreement */}
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={agreed}
                  onChange={(e) => setAgreed(e.target.checked)}
                  className="checkbox-input"
                />
                <span className="checkbox-custom"></span>
                <span className="checkbox-text">
                  이용약관 및 개인정보처리방침에 동의합니다
                </span>
              </label>

              {/* Error Message */}
              {error && (
                <div className="error-message">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 8v4M12 16h.01"/>
                  </svg>
                  {error}
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                className="btn btn-primary login-btn"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="spinner"></span>
                    시작 중...
                  </>
                ) : (
                  <>
                    시작하기
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M5 12h14M12 5l7 7-7 7"/>
                    </svg>
                  </>
                )}
              </button>
            </form>

            {/* Footer */}
            <div className="login-footer">
              <div className="footer-divider">
                <span>Developed by</span>
              </div>
              <a href="https://psid.khu.ac.kr/main.do" target="_blank" rel="noopener noreferrer" className="lab-link">
                KHU PSID Laboratory
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
