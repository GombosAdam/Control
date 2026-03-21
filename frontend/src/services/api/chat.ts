import api from './client';

export interface ChatResponse {
  answer: string;
  sql: string | null;
  error: string | null;
  row_count: number | null;
  response_time_ms: number | null;
  sql_generation_ms: number | null;
  retry_count: number;
  model_used: string | null;
}

export const chatApi = {
  ask: (question: string) =>
    api.post<ChatResponse>('/chat/ask', { question }).then(r => r.data),
};
