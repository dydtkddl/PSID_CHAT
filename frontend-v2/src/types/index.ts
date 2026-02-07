// Type definitions for KyungHee Chatbot V2

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: Source[];
}

export interface Source {
  filename: string;
  page?: number;
  articleNumber?: number;
  clauseNumber?: number;
  uri?: string;
}

export interface Category {
  slug: string;
  label: string;
  hasCohort: boolean;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  category: string;
  cohort: string | null;
}

export interface User {
  memberId: string;
  isAuthenticated: boolean;
}
