import type {
  Session,
  SessionCreate,
  SessionListResponse,
  RunStartResponse,
  WorkflowStatusResponse,
  Report,
  ChatHistoryResponse,
  ChatMessage,
} from "../types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore parse failure
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  createSession(data: SessionCreate): Promise<Session> {
    return request("/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  listSessions(): Promise<SessionListResponse> {
    return request("/sessions");
  },

  getSession(id: string): Promise<Session> {
    return request(`/sessions/${id}`);
  },

  startRun(sessionId: string): Promise<RunStartResponse> {
    return request(`/sessions/${sessionId}/run`, { method: "POST" });
  },

  getWorkflowStatus(sessionId: string): Promise<WorkflowStatusResponse> {
    return request(`/sessions/${sessionId}/workflow`);
  },

  getReport(sessionId: string): Promise<Report> {
    return request(`/sessions/${sessionId}/report`);
  },

  getChatMessages(sessionId: string): Promise<ChatHistoryResponse> {
    return request(`/sessions/${sessionId}/chat`);
  },

  sendMessage(sessionId: string, message: string): Promise<ChatMessage> {
    return request(`/sessions/${sessionId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  },
};
