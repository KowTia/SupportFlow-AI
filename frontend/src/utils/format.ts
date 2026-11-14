import type {
  DeliveryStatus,
  TicketCategory,
  TicketPriority,
  TicketStatus,
} from "../types/api";

export const STATUS_OPTIONS: TicketStatus[] = [
  "new",
  "processing",
  "awaiting_review",
  "approved",
  "routed",
  "failed",
];

export const PRIORITY_OPTIONS: TicketPriority[] = ["low", "medium", "high", "critical"];

export const CATEGORY_OPTIONS: TicketCategory[] = [
  "billing",
  "technical",
  "account",
  "feature_request",
  "security",
  "other",
];

export const ASSIGNED_TEAM_OPTIONS = [
  "billing_ops",
  "tech_support",
  "account_security",
  "product_team",
  "general_support",
] as const;

export const STATUS_STYLES: Record<TicketStatus, { label: string; className: string }> = {
  new: {
    label: "NEW",
    className: "bg-slate-100 text-slate-700 border-slate-200",
  },
  processing: {
    label: "PROCESSING",
    className: "bg-blue-50 text-blue-700 border-blue-200",
  },
  awaiting_review: {
    label: "AWAITING REVIEW",
    className: "bg-amber-50 text-amber-800 border-amber-200",
  },
  approved: {
    label: "APPROVED",
    className: "bg-indigo-50 text-indigo-700 border-indigo-200",
  },
  routed: {
    label: "ROUTED",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  failed: {
    label: "FAILED",
    className: "bg-red-50 text-red-700 border-red-200",
  },
};

export const PRIORITY_STYLES: Record<TicketPriority, { label: string; className: string }> = {
  low: {
    label: "LOW",
    className: "bg-slate-100 text-slate-600 border-slate-200",
  },
  medium: {
    label: "MEDIUM",
    className: "bg-sky-50 text-sky-700 border-sky-200",
  },
  high: {
    label: "HIGH",
    className: "bg-amber-50 text-amber-800 border-amber-200",
  },
  critical: {
    label: "CRITICAL",
    className: "bg-red-50 text-red-700 border-red-200",
  },
};

export const DELIVERY_STATUS_STYLES: Record<
  DeliveryStatus,
  { label: string; className: string }
> = {
  pending: {
    label: "PENDING",
    className: "bg-slate-100 text-slate-700 border-slate-200",
  },
  success: {
    label: "SUCCESS",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  dry_run: {
    label: "DRY RUN",
    className: "bg-blue-50 text-blue-700 border-blue-200",
  },
  failed: {
    label: "FAILED",
    className: "bg-red-50 text-red-700 border-red-200",
  },
};

export function formatCategory(category: TicketCategory | string | null | undefined): string {
  if (!category) return "unclassified";
  return category.replace(/_/g, " ");
}

export function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatPercent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}
