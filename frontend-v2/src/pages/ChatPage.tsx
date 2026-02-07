import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ChatPage.css';
import * as api from '../api';
import type { ChatMessage, SourceDocument, ChatSessionSummary, Bookmark } from '../api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface Source {
  id: string;
  title: string;
  article: string | null;
  relevance: number;
  content?: string;
}

interface Category {
  slug: string;
  label: string;
  hasCohort: boolean;
}

const CATEGORIES: Category[] = [
  { slug: 'regulations', label: '규정', hasCohort: false },
  { slug: 'undergrad_rules', label: '학부 시행세칙', hasCohort: true },
  { slug: 'grad_rules', label: '대학원 시행세칙', hasCohort: true },
  { slug: 'academic_system', label: '학사제도', hasCohort: false },
];

const COHORTS = ['2025', '2024', '2023', '2022', '2021', '2020'];

interface ChatPageProps {
  onLogout: () => void;
  memberId: string;
}

export default function ChatPage({ onLogout, memberId }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: '경희대학교 규정 검색 어시스턴트에 오신 것을 환영합니다.\n\n수강신청, 장학금 자격, 학적 규정 등에 대해 질문해 주세요.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [category, setCategory] = useState('undergrad_rules');
  const [cohort, setCohort] = useState<string | null>('2025');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [rightPanelTab, setRightPanelTab] = useState<'sources' | 'history'>('history');
  const [sources, setSources] = useState<Source[]>([]);
  const [history, setHistory] = useState<ChatSessionSummary[]>([]);
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [apiError, setApiError] = useState<string | null>(null);
  const [expandedSource, setExpandedSource] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const selectedCategory = CATEGORIES.find((c) => c.slug === category);

  // Load history and bookmarks on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const [historyData, bookmarksData] = await Promise.all([
          api.getHistory(memberId).catch(() => []),
          api.getBookmarks(memberId).catch(() => []),
        ]);
        setHistory(historyData);
        setBookmarks(bookmarksData);
      } catch (e) {
        console.error('Failed to load data:', e);
      }
    };
    loadData();
  }, [memberId]);

  useEffect(() => {
    if (selectedCategory?.hasCohort && !cohort) {
      setCohort('2023');
    } else if (!selectedCategory?.hasCohort) {
      setCohort(null);
    }
  }, [category, selectedCategory, cohort]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setApiError(null);

    try {
      // Convert messages to API format
      const chatHistory: ChatMessage[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Call the actual API
      const response = await api.sendMessage(
        input,
        category,
        cohort,
        chatHistory,
        memberId
      );

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Update sources from response
      const newSources: Source[] = response.sources.map((s: SourceDocument) => ({
        id: s.id,
        title: s.title,
        article: s.article || null,
        relevance: s.relevance || 0,
        content: s.content,
      }));
      setSources(newSources);

      // Refresh history
      const updatedHistory = await api.getHistory(memberId).catch(() => []);
      setHistory(updatedHistory);

    } catch (error) {
      console.error('API Error:', error);
      setApiError(error instanceof Error ? error.message : 'API 연결 오류');
      
      // Fallback demo response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `⚠️ Backend 연결 실패: ${error instanceof Error ? error.message : 'Unknown error'}\n\n📎 *Please start the FastAPI backend server with:*\n\`cd backend && uvicorn main:app --host 0.0.0.0 --port 8501\``,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, messages, category, cohort, memberId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    setMessages([{
      id: '1',
      role: 'assistant',
      content: '경희대학교 규정 검색 어시스턴트에 오신 것을 환영합니다.\n\n수강신청, 장학금 자격, 학적 규정 등에 대해 질문해 주세요.',
      timestamp: new Date(),
    }]);
    setSources([]);
    setExpandedSource(null);
    setRightPanelTab('sources');
    setInput('');
  };

  const handleAddBookmark = async (source: Source) => {
    try {
      const newBookmark = await api.addBookmark(
        memberId,
        source.title,
        source.article,
        null,
        category
      );
      setBookmarks((prev) => [...prev, newBookmark]);
    } catch (e) {
      console.error('Failed to add bookmark:', e);
    }
  };

  const handleDeleteBookmark = async (bookmarkId: string) => {
    try {
      await api.deleteBookmark(bookmarkId, memberId);
      setBookmarks((prev) => prev.filter((b) => b.id !== bookmarkId));
    } catch (e) {
      console.error('Failed to delete bookmark:', e);
    }
  };

  // 히스토리 세션 로드
  const handleLoadSession = async (sessionId: string) => {
    try {
      const session = await api.getSession(sessionId, memberId);
      if (session && session.messages) {
        // 메시지 형식 변환
        const loadedMessages = session.messages.map((msg: any, idx: number) => ({
          id: String(idx + 1),
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
          timestamp: new Date(),
        }));
        setMessages(loadedMessages);
        
        // 카테고리 설정
        if (session.category) {
          setCategory(session.category);
        }
        if (session.cohort) {
          setCohort(session.cohort);
        }
        
        // 참조문서 탭으로 전환
        setRightPanelTab('sources');
      }
    } catch (e) {
      console.error('Failed to load session:', e);
    }
  };

  return (
    <div className="chat-layout">
      {/* Left Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <svg viewBox="0 0 40 40" className="magnolia-icon">
              <circle cx="20" cy="20" r="18" fill="none" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M20 8 C20 8 12 14 12 22 C12 28 16 32 20 32 C24 32 28 28 28 22 C28 14 20 8 20 8" fill="currentColor" opacity="0.3"/>
              <path d="M20 10 C18 14 16 18 16 22 C16 26 18 30 20 30" fill="none" stroke="currentColor" strokeWidth="1"/>
              <path d="M20 10 C22 14 24 18 24 22 C24 26 22 30 20 30" fill="none" stroke="currentColor" strokeWidth="1"/>
            </svg>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button className="nav-item active" title="Search Regulations">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <span>Search</span>
          </button>
          <button className="nav-item" title="Chat History" onClick={() => setRightPanelTab('history')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span>History</span>
          </button>
          <button className="nav-item" title="Bookmarks" onClick={() => setRightPanelTab('sources')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
            </svg>
            <span>Bookmarks</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <button className="nav-item" title="Settings">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            <span>Settings</span>
          </button>
          <button className="nav-item" onClick={onLogout} title="Log Out">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            <span>Log Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="chat-main">
        {/* Header */}
        <header className="chat-header">
          <button className="mobile-menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          
          <div className="header-brand">
            <img 
              src="/asset/kyunghee.png" 
              alt="KHU" 
              className="header-logo"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <div className="header-title-group">
              <h1 className="header-title">경희대학교 규정 검색</h1>
              <div className="header-subtitle">학교 규정 및 시행세칙 안내</div>
            </div>
          </div>

          <div className="header-controls">
            <select
              className="select-field category-select"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {CATEGORIES.map((cat) => (
                <option key={cat.slug} value={cat.slug}>{cat.label}</option>
              ))}
            </select>

            {selectedCategory?.hasCohort && (
              <select
                className="select-field cohort-select"
                value={cohort || ''}
                onChange={(e) => setCohort(e.target.value)}
              >
                {COHORTS.map((y) => (
                  <option key={y} value={y}>{y}학번</option>
                ))}
              </select>
            )}

            <div className="user-badge">
              <span className="user-icon">👤</span>
              <span className="user-id">{memberId}</span>
            </div>
          </div>
        </header>

        {/* API Error Banner */}
        {apiError && (
          <div className="api-error-banner">
            ⚠️ {apiError} - Backend 서버를 실행해주세요
          </div>
        )}

        {/* Chat Area with Watermark */}
        <div className="chat-area">
          <div className="chat-watermark">
            <svg viewBox="0 0 200 200" className="watermark-svg">
              <path d="M100 20 C80 40 60 70 60 100 C60 140 80 170 100 180 C120 170 140 140 140 100 C140 70 120 40 100 20" fill="none" stroke="currentColor" strokeWidth="0.5"/>
              <path d="M100 30 C85 50 75 75 75 100 C75 130 85 155 100 165" fill="none" stroke="currentColor" strokeWidth="0.5"/>
              <path d="M100 30 C115 50 125 75 125 100 C125 130 115 155 100 165" fill="none" stroke="currentColor" strokeWidth="0.5"/>
              <circle cx="100" cy="100" r="80" fill="none" stroke="currentColor" strokeWidth="0.3"/>
            </svg>
          </div>

          <div className="chat-messages">
            {messages.map((msg) => (
              <div key={msg.id} className={`message-wrapper ${msg.role}`}>
                <div className={`message-avatar ${msg.role}`}>
                  {msg.role === 'assistant' ? (
                    <svg viewBox="0 0 32 32" className="avatar-icon">
                      <rect x="8" y="18" width="16" height="10" fill="currentColor" opacity="0.3"/>
                      <path d="M16 6 L6 16 H26 L16 6" fill="currentColor" opacity="0.5"/>
                      <rect x="10" y="20" width="4" height="6" fill="currentColor" opacity="0.5"/>
                      <rect x="18" y="20" width="4" height="6" fill="currentColor" opacity="0.5"/>
                      <path d="M16 8 L16 14" stroke="currentColor" strokeWidth="1"/>
                    </svg>
                  ) : (
                    <span className="user-initial">{memberId.charAt(0).toUpperCase()}</span>
                  )}
                </div>

                <div className={`chat-bubble chat-bubble-${msg.role}`}>
                  <div className="bubble-text markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="message-wrapper assistant">
                <div className="message-avatar assistant">
                  <svg viewBox="0 0 32 32" className="avatar-icon">
                    <rect x="8" y="18" width="16" height="10" fill="currentColor" opacity="0.3"/>
                    <path d="M16 6 L6 16 H26 L16 6" fill="currentColor" opacity="0.5"/>
                    <rect x="10" y="20" width="4" height="6" fill="currentColor" opacity="0.5"/>
                    <rect x="18" y="20" width="4" height="6" fill="currentColor" opacity="0.5"/>
                  </svg>
                </div>
                <div className="chat-bubble chat-bubble-assistant">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Section */}
        <footer className="chat-input-section">
          <div className="input-container glass-card">
            <textarea
              className="chat-input"
              placeholder="규정에 대해 묶어보세요... (ex: 장학금 수혜 자격, 조기졸업 조건)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isLoading}
            />
            <button
              className="send-button"
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              aria-label="Send"
            >
              {isLoading ? (
                <span className="spinner"></span>
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M20 2L8 14"/>
                  <path d="M20 2L14 22L11 13L2 10L20 2"/>
                </svg>
              )}
            </button>
          </div>
          <div className="input-hint">
            Enter 키로 전송 · Shift+Enter로 줄바꿈
          </div>
        </footer>
      </main>

      {/* Right Panel - Sources & History */}
      <aside className="right-panel">
        {/* Tab Navigation */}
        <div className="panel-tabs">
          <button 
            className={`panel-tab ${rightPanelTab === 'sources' ? 'active' : ''}`}
            onClick={() => setRightPanelTab('sources')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            참조문서
          </button>
          <button 
            className={`panel-tab ${rightPanelTab === 'history' ? 'active' : ''}`}
            onClick={() => setRightPanelTab('history')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            기록
          </button>
        </div>

        {/* Panel Content */}
        <div className="panel-content">
          {rightPanelTab === 'sources' ? (
            <div className="sources-panel">
              <h3 className="panel-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                </svg>
                참조 문서
              </h3>
              
              {sources.length > 0 ? (
                <div className="source-list">
                  {sources.map((source) => (
                    <div 
                      key={source.id} 
                      className={`source-item ${expandedSource === source.id ? 'expanded' : ''}`}
                      onClick={() => setExpandedSource(expandedSource === source.id ? null : source.id)}
                    >
                      <div className="source-header">
                        <span className="source-title">
                          {source.title || source.content?.slice(0, 50) || '문서'}
                        </span>
                        <span className="source-relevance">{source.relevance}%</span>
                      </div>
                      {source.article && <div className="source-article">{source.article}</div>}
                      
                      {/* 청크 내용 미리보기 / 확장 */}
                      {expandedSource === source.id ? (
                        <div className="source-content-full">
                          <p>{source.content || '내용 없음'}</p>
                        </div>
                      ) : (
                        <div className="source-content-preview">
                          {source.content?.slice(0, 80)}...
                        </div>
                      )}
                      
                      <button 
                        className="bookmark-btn"
                        onClick={(e) => { e.stopPropagation(); handleAddBookmark(source); }}
                        title="즐겨찾기 추가"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                  <p>질문을 하시면 관련 문서가 표시됩니다</p>
                </div>
              )}

              <div className="panel-section">
                <h4 className="section-title">즐겨찾기</h4>
                <div className="bookmark-list">
                  {bookmarks.length > 0 ? (
                    bookmarks.map((bookmark) => (
                      <div key={bookmark.id} className="bookmark-item">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                        </svg>
                        <span>{bookmark.title}</span>
                        <button 
                          className="delete-btn"
                          onClick={() => handleDeleteBookmark(bookmark.id)}
                        >×</button>
                      </div>
                    ))
                  ) : (
                    <p className="empty-hint">즐겨찾기가 없습니다</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="history-panel">
              <h3 className="panel-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                대화 기록
              </h3>

              <button className="new-chat-btn" onClick={handleNewChat}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                새 대화 시작
              </button>

              <div className="history-list">
                {history.length > 0 ? (
                  history.map((session) => (
                    <div 
                      key={session.id} 
                      className="history-item"
                      onClick={() => handleLoadSession(session.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <div className="history-date">{session.date}</div>
                      <div className="history-title">{session.title}</div>
                      <div className="history-preview">{session.preview}</div>
                    </div>
                  ))
                ) : (
                  <p className="empty-hint">대화 기록이 없습니다</p>
                )}
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}
    </div>
  );
}
