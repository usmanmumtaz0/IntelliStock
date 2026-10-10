import { apiRequest } from "./client";

export interface Conversation {
  id: string;
  title: string;
  turn_count: number;
  updated_at: string;
}
export interface ChatSource {
  kind: string;
  id: string;
  label: string;
  href: string;
}
export interface ChatTurn {
  id: string;
  request_id: string;
  sequence: number;
  question: string;
  answer: string;
  sources: ChatSource[];
  mode: "local" | "openai" | "openrouter" | "fallback";
  notice: string | null;
  created_at: string;
}
export interface ChatStatus {
  provider: string;
  provider_ready: boolean;
  read_only: boolean;
  max_turns: number;
  data_policy: string;
}
export const chat = {
  status: () => apiRequest<ChatStatus>("/chat/status"),
  conversations: () => apiRequest<Conversation[]>("/chat/conversations"),
  create: () => apiRequest<Conversation>("/chat/conversations", { method: "POST" }),
  get: (id: string) =>
    apiRequest<{ id: string; title: string; turns: ChatTurn[] }>(
      `/chat/conversations/${encodeURIComponent(id)}`,
    ),
  remove: (id: string) =>
    apiRequest<void>(`/chat/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }),
  ask: (id: string, input: { request_id: string; question: string }) =>
    apiRequest<ChatTurn>(`/chat/conversations/${encodeURIComponent(id)}/turns`, {
      method: "POST",
      body: JSON.stringify(input),
      signal: AbortSignal.timeout(45_000),
    }),
};

/** Sources are internal record references, never model-provided external URLs. */
export function safeSourceHref(value: string): string | null {
  if (/[\s\\]/.test(value)) return null;
  return /^\/(inventory|alerts|reports)(\?[^\\\r\n]*)?$/.test(value) ? value : null;
}
