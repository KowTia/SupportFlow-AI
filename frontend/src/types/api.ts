export type TicketStatus =
  | "new"
  | "processing"
  | "awaiting_review"
  | "approved"
  | "routed"
  | "failed";

export type TicketPriority = "low" | "medium" | "high" | "critical";

export type TicketCategory =
  | "billing"
  | "technical"
  | "account"
  | "feature_request"
  | "security"
  | "other";

export type DeliveryTarget = "webhook" | "google_sheets";

export type DeliveryStatus = "pending" | "success" | "dry_run" | "failed";

export interface TicketCreatePayload {
  subject: string;
  body: string;
  source?: string;
  customer_email?: string | null;
  customer_name?: string | null;
  idempotency_key?: string | null;
  metadata_json?: Record<string, unknown>;
}

export interface TicketUpdatePayload {
  status?: TicketStatus;
  category?: TicketCategory;
  priority?: TicketPriority;
  assigned_team?: string;
  draft_reply?: string;
}

export interface TicketApprovePayload {
  category?: TicketCategory;
  priority?: TicketPriority;
  assigned_team?: string;
  draft_reply?: string;
}

export interface TicketAnalysis {
  id: string;
  ticket_id: string;
  provider: string;
  model: string;
  category: TicketCategory;
  priority: TicketPriority;
  assigned_team: string;
  summary: string;
  draft_reply: string;
  confidence: number;
  needs_human_review: boolean;
  reasoning: string;
  cited_kb_ids: string[];
  injection_detected: boolean;
  injection_risk_score: number;
  injection_patterns: string[];
  repair_attempts: number;
  fallback_used: boolean;
  latency_ms: number;
  created_at: string;
}

export interface DeliveryLog {
  id: string;
  ticket_id: string;
  target: DeliveryTarget;
  endpoint: string | null;
  status: DeliveryStatus;
  status_code: number | null;
  attempt: number;
  request_payload: Record<string, unknown> | null;
  response_body: string | null;
  error_message: string | null;
  created_at: string;
}

export interface Ticket {
  id: string;
  idempotency_key: string;
  source: string;
  customer_email: string | null;
  customer_name: string | null;
  subject: string;
  body: string;
  status: TicketStatus;
  category: TicketCategory | null;
  priority: TicketPriority | null;
  assigned_team: string | null;
  draft_reply: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  delivery_logs: DeliveryLog[];
  analyses: TicketAnalysis[];
}

export interface TicketListResponse {
  items: Ticket[];
  total: number;
  limit: number;
  offset: number;
}

export interface KBArticle {
  id: string;
  slug: string;
  title: string;
  category: TicketCategory;
  content: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface KBArticleCreatePayload {
  slug: string;
  title: string;
  category: TicketCategory;
  content: string;
  tags: string[];
}

export interface KBArticleListResponse {
  items: KBArticle[];
  total: number;
  limit: number;
  offset: number;
}

export interface KBSearchRequest {
  query: string;
  category?: TicketCategory | null;
  top_k?: number;
  min_score?: number;
}

export interface KBSearchHit {
  article: KBArticle;
  score: number;
}

export interface KBSearchResponse {
  query: string;
  hits: KBSearchHit[];
}

export interface KBSeedResponse {
  created: number;
  updated: number;
  total: number;
}

export interface DashboardMetrics {
  total_tickets: number;
  tickets_by_status: Record<string, number>;
  tickets_by_category: Record<string, number>;
  tickets_by_priority: Record<string, number>;
  total_analyses: number;
  avg_confidence: number;
  avg_latency_ms: number;
  human_review_rate: number;
  injection_detected_count: number;
  total_repair_attempts: number;
  total_deliveries: number;
  deliveries_by_status: Record<string, number>;
  deliveries_by_target: Record<string, number>;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  environment: string;
  database: string;
}
