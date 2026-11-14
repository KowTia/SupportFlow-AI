import type {
  DashboardMetrics,
  HealthStatus,
  KBArticle,
  KBArticleCreatePayload,
  KBArticleListResponse,
  KBSearchRequest,
  KBSearchResponse,
  KBSeedResponse,
  Ticket,
  TicketApprovePayload,
  TicketCategory,
  TicketCreatePayload,
  TicketListResponse,
  TicketPriority,
  TicketStatus,
  TicketUpdatePayload,
} from "../types/api";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function buildUrl(path: string, query?: Record<string, string | number | boolean | undefined>): string {
  const url = `${API_BASE_URL}${path}`;
  if (!query) return url;

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return JSON.stringify(item);
        })
        .join("; ");
    }
  } catch {
    // Fallback to HTTP status text when body is not JSON
  }
  return response.statusText || `HTTP ${response.status}`;
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<{ data: T; response: Response }> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }

  if (response.status === 204) {
    return { data: undefined as T, response };
  }

  const data = (await response.json()) as T;
  return { data, response };
}

export const apiClient = {
  async getHealth(): Promise<HealthStatus> {
    const { data } = await requestJson<HealthStatus>(buildUrl("/healthz"));
    return data;
  },

  async createTicket(
    payload: TicketCreatePayload,
    options?: { idempotencyKey?: string; autoAnalyze?: boolean },
  ): Promise<{ ticket: Ticket; idempotentReplay: boolean }> {
    const headers: Record<string, string> = {};
    if (options?.idempotencyKey?.trim()) {
      headers["Idempotency-Key"] = options.idempotencyKey.trim();
    }

    const { data, response } = await requestJson<Ticket>(
      buildUrl("/api/v1/tickets", {
        auto_analyze: options?.autoAnalyze ?? false,
      }),
      {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      },
    );

    const replayHeader = response.headers.get("X-Idempotent-Replay");
    return {
      ticket: data,
      idempotentReplay: replayHeader === "true" || response.status === 200,
    };
  },

  async listTickets(params?: {
    status?: TicketStatus;
    priority?: TicketPriority;
    category?: TicketCategory;
    limit?: number;
    offset?: number;
  }): Promise<TicketListResponse> {
    const { data } = await requestJson<TicketListResponse>(
      buildUrl("/api/v1/tickets", {
        status: params?.status,
        priority: params?.priority,
        category: params?.category,
        limit: params?.limit ?? 50,
        offset: params?.offset ?? 0,
      }),
    );
    return data;
  },

  async getTicket(ticketId: string): Promise<Ticket> {
    const { data } = await requestJson<Ticket>(buildUrl(`/api/v1/tickets/${ticketId}`));
    return data;
  },

  async updateTicket(ticketId: string, payload: TicketUpdatePayload): Promise<Ticket> {
    const { data } = await requestJson<Ticket>(buildUrl(`/api/v1/tickets/${ticketId}`), {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    return data;
  },

  async analyzeTicket(ticketId: string): Promise<Ticket> {
    const { data } = await requestJson<Ticket>(buildUrl(`/api/v1/tickets/${ticketId}/analyze`), {
      method: "POST",
    });
    return data;
  },

  async approveTicket(ticketId: string, payload?: TicketApprovePayload): Promise<Ticket> {
    const { data } = await requestJson<Ticket>(buildUrl(`/api/v1/tickets/${ticketId}/approve`), {
      method: "POST",
      body: JSON.stringify(payload ?? {}),
    });
    return data;
  },

  async listKBArticles(params?: {
    category?: TicketCategory;
    limit?: number;
    offset?: number;
  }): Promise<KBArticleListResponse> {
    const { data } = await requestJson<KBArticleListResponse>(
      buildUrl("/api/v1/kb", {
        category: params?.category,
        limit: params?.limit ?? 50,
        offset: params?.offset ?? 0,
      }),
    );
    return data;
  },

  async upsertKBArticle(payload: KBArticleCreatePayload): Promise<KBArticle> {
    const { data } = await requestJson<KBArticle>(buildUrl("/api/v1/kb"), {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return data;
  },

  async seedKBArticles(): Promise<KBSeedResponse> {
    const { data } = await requestJson<KBSeedResponse>(buildUrl("/api/v1/kb/seed"), {
      method: "POST",
    });
    return data;
  },

  async searchKB(payload: KBSearchRequest): Promise<KBSearchResponse> {
    const { data } = await requestJson<KBSearchResponse>(buildUrl("/api/v1/kb/search"), {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return data;
  },

  async deleteKBArticle(articleId: string): Promise<void> {
    await requestJson<void>(buildUrl(`/api/v1/kb/${articleId}`), {
      method: "DELETE",
    });
  },

  async getMetrics(): Promise<DashboardMetrics> {
    const { data } = await requestJson<DashboardMetrics>(buildUrl("/api/v1/metrics"));
    return data;
  },
};
