// API Client for KHU Regulation Assistant Backend

// nginx 프록시를 통해 /khu_chatbot/api/ 로 접근
const API_BASE = '/khu_chatbot/api';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface SourceDocument {
  id: string;
  title: string;
  article?: string;
  content: string;
  relevance?: number;
  uri?: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceDocument[];
  session_id: string;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  date: string;
  preview: string;
  category: string;
}

export interface Bookmark {
  id: string;
  member_id: string;
  title: string;
  article?: string;
  uri?: string;
  category: string;
  created_at: string;
}

// ─────────────────────────────────────────────────────────────
// Chat API
// ─────────────────────────────────────────────────────────────

export async function sendMessage(
  message: string,
  category: string,
  cohort: string | null,
  history: ChatMessage[],
  memberId: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      category,
      cohort,
      history,
      member_id: memberId,
    }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Chat request failed');
  }
  
  return response.json();
}

// ─────────────────────────────────────────────────────────────
// History API
// ─────────────────────────────────────────────────────────────

export async function getHistory(memberId: string): Promise<ChatSessionSummary[]> {
  const response = await fetch(`${API_BASE}/history?member_id=${encodeURIComponent(memberId)}`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch history');
  }
  
  return response.json();
}

export async function getSession(sessionId: string, memberId: string): Promise<any> {
  const response = await fetch(
    `${API_BASE}/history/${sessionId}?member_id=${encodeURIComponent(memberId)}`
  );
  
  if (!response.ok) {
    throw new Error('Failed to fetch session');
  }
  
  return response.json();
}

export async function deleteSession(sessionId: string, memberId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/history/${sessionId}?member_id=${encodeURIComponent(memberId)}`,
    { method: 'DELETE' }
  );
  
  if (!response.ok) {
    throw new Error('Failed to delete session');
  }
}

// ─────────────────────────────────────────────────────────────
// Bookmarks API
// ─────────────────────────────────────────────────────────────

export async function getBookmarks(memberId: string): Promise<Bookmark[]> {
  const response = await fetch(`${API_BASE}/bookmarks?member_id=${encodeURIComponent(memberId)}`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch bookmarks');
  }
  
  return response.json();
}

export async function addBookmark(
  memberId: string,
  title: string,
  article: string | null,
  uri: string | null,
  category: string
): Promise<Bookmark> {
  const response = await fetch(`${API_BASE}/bookmarks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      member_id: memberId,
      title,
      article,
      uri,
      category,
    }),
  });
  
  if (!response.ok) {
    throw new Error('Failed to add bookmark');
  }
  
  return response.json();
}

export async function deleteBookmark(bookmarkId: string, memberId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/bookmarks/${bookmarkId}?member_id=${encodeURIComponent(memberId)}`,
    { method: 'DELETE' }
  );
  
  if (!response.ok) {
    throw new Error('Failed to delete bookmark');
  }
}
