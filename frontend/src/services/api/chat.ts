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

export interface ToolCallLog {
  tool: string;
  params: Record<string, unknown>;
  latency_ms: number;
}

export interface AgentResponse {
  answer: string;
  tool_calls: ToolCallLog[];
  response_time_ms: number | null;
  model_used: string | null;
  error: string | null;
}

export const chatApi = {
  ask: (question: string) =>
    api.post<ChatResponse>('/chat/ask', { question }).then(r => r.data),
};

export const agentApi = {
  ask: (question: string) =>
    api.post<AgentResponse>('/agent/ask', { question }).then(r => r.data),
};
