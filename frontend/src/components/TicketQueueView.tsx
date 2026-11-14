import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  RefreshCw,
  Save,
  Send,
  ShieldAlert,
  Webhook,
} from "lucide-react";

import { apiClient, ApiError } from "../api/client";
import type {
  Ticket,
  TicketCategory,
  TicketPriority,
  TicketStatus,
} from "../types/api";
import {
  ASSIGNED_TEAM_OPTIONS,
  CATEGORY_OPTIONS,
  DELIVERY_STATUS_STYLES,
  formatCategory,
  formatPercent,
  formatTimestamp,
  PRIORITY_OPTIONS,
  PRIORITY_STYLES,
  STATUS_OPTIONS,
  STATUS_STYLES,
} from "../utils/format";

interface TicketQueueViewProps {
  selectedTicketId: string | null;
  onSelectTicket: (ticketId: string | null) => void;
}

export function TicketQueueView({
  selectedTicketId,
  onSelectTicket,
}: TicketQueueViewProps) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionBanner, setActionBanner] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<TicketStatus | "">("");
  const [priorityFilter, setPriorityFilter] = useState<TicketPriority | "">("");
  const [categoryFilter, setCategoryFilter] = useState<TicketCategory | "">("");

  const [editCategory, setEditCategory] = useState<TicketCategory>("other");
  const [editPriority, setEditPriority] = useState<TicketPriority>("medium");
  const [editTeam, setEditTeam] = useState<string>("general_support");
  const [editDraftReply, setEditDraftReply] = useState<string>("");

  const [busyAction, setBusyAction] = useState<
    "analyze" | "save" | "approve" | null
  >(null);
  const [expandedLogIds, setExpandedLogIds] = useState<Record<string, boolean>>({});
  const [showReasoning, setShowReasoning] = useState(false);

  const loadTickets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.listTickets({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        category: categoryFilter || undefined,
        limit: 50,
      });
      setTickets(response.items);
      setTotal(response.total);
      if (response.items.length > 0) {
        const stillExists = response.items.some((t) => t.id === selectedTicketId);
        if (!selectedTicketId || !stillExists) {
          onSelectTicket(response.items[0].id);
        }
      } else {
        onSelectTicket(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to fetch tickets.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter, categoryFilter, selectedTicketId, onSelectTicket]);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  const selectedTicket = useMemo(
    () => tickets.find((t) => t.id === selectedTicketId) ?? null,
    [tickets, selectedTicketId],
  );

  useEffect(() => {
    if (!selectedTicket) return;
    setEditCategory(selectedTicket.category ?? "other");
    setEditPriority(selectedTicket.priority ?? "medium");
    setEditTeam(selectedTicket.assigned_team ?? "general_support");
    setEditDraftReply(selectedTicket.draft_reply ?? "");
    setActionBanner(null);
    setShowReasoning(false);
  }, [selectedTicket?.id, selectedTicket?.updated_at]);

  const mergeUpdatedTicket = (updated: Ticket) => {
    setTickets((prev) =>
      prev.map((item) => (item.id === updated.id ? updated : item)),
    );
    onSelectTicket(updated.id);
  };

  const handleAnalyze = async () => {
    if (!selectedTicket) return;
    setBusyAction("analyze");
    setError(null);
    setActionBanner(null);
    try {
      const updated = await apiClient.analyzeTicket(selectedTicket.id);
      mergeUpdatedTicket(updated);
      setActionBanner("RAG + LLM triage analysis completed and saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "AI triage failed.");
    } finally {
      setBusyAction(null);
    }
  };

  const handleSaveEdits = async () => {
    if (!selectedTicket) return;
    setBusyAction("save");
    setError(null);
    setActionBanner(null);
    try {
      const updated = await apiClient.updateTicket(selectedTicket.id, {
        category: editCategory,
        priority: editPriority,
        assigned_team: editTeam,
        draft_reply: editDraftReply,
      });
      mergeUpdatedTicket(updated);
      setActionBanner("Operator edits saved to PostgreSQL.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to save edits.");
    } finally {
      setBusyAction(null);
    }
  };

  const handleApproveAndRoute = async () => {
    if (!selectedTicket) return;
    setBusyAction("approve");
    setError(null);
    setActionBanner(null);
    try {
      const updated = await apiClient.approveTicket(selectedTicket.id, {
        category: editCategory,
        priority: editPriority,
        assigned_team: editTeam,
        draft_reply: editDraftReply,
      });
      mergeUpdatedTicket(updated);
      setActionBanner(
        `Ticket approved and dispatched (${updated.delivery_logs.length} outbound delivery record(s)).`,
      );
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Approval & outbound dispatch failed.",
      );
    } finally {
      setBusyAction(null);
    }
  };

  const latestAnalysis = selectedTicket?.analyses[0] ?? null;

  const toggleLogExpand = (logId: string) => {
    setExpandedLogIds((prev) => ({ ...prev, [logId]: !prev[logId] }));
  };

  const pipelineStages = useMemo(() => {
    if (!selectedTicket) return [];
    const hasAnalysis = Boolean(latestAnalysis);
    const hasInjection = Boolean(latestAnalysis?.injection_detected);
    const hasDelivery = selectedTicket.delivery_logs.length > 0;
    return [
      { label: "1. Ingest", active: true, tone: "ok" as const },
      {
        label: hasInjection ? "2. Guard Flagged" : "2. Prompt Guard",
        active: hasAnalysis,
        tone: hasInjection ? ("danger" as const) : ("ok" as const),
      },
      {
        label: `3. RAG (${latestAnalysis?.cited_kb_ids.length ?? 0} KB)`,
        active: hasAnalysis,
        tone: "ok" as const,
      },
      {
        label: `4. LLM (R:${latestAnalysis?.repair_attempts ?? 0})`,
        active: hasAnalysis,
        tone: (latestAnalysis?.repair_attempts ?? 0) > 0 ? ("warn" as const) : ("ok" as const),
      },
      {
        label: `5. Dispatch (${selectedTicket.delivery_logs.length})`,
        active: hasDelivery,
        tone: "ok" as const,
      },
    ];
  }, [selectedTicket, latestAnalysis]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="font-mono text-xs font-medium uppercase tracking-wider text-blue-600">
            02 // Operator Workbench &amp; Routing Audit
          </p>
          <h2 className="mt-1 font-display text-2xl font-bold tracking-tight text-slate-900">
            Ticket Triage Queue
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Review AI classification, edit draft replies, approve escalation, and inspect signed HMAC &amp; Sheets logs.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Filter by status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as TicketStatus | "")}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700"
          >
            <option value="">All Statuses</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by priority"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as TicketPriority | "")}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700"
          >
            <option value="">All Priorities</option>
            {PRIORITY_OPTIONS.map((prio) => (
              <option key={prio} value={prio}>
                {prio}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by category"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as TicketCategory | "")}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700"
          >
            <option value="">All Categories</option>
            {CATEGORY_OPTIONS.map((cat) => (
              <option key={cat} value={cat}>
                {formatCategory(cat)}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => void loadTickets()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh ({total})
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {actionBanner && (
        <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-800">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{actionBanner}</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm xl:col-span-4">
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2.5">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-600">
              Queue ({tickets.length} / {total})
            </span>
            <span className="font-mono text-[11px] text-slate-400">Newest first</span>
          </div>

          <div className="max-h-[720px] divide-y divide-slate-100 overflow-y-auto">
            {tickets.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500">
                {loading
                  ? "Loading tickets..."
                  : "No tickets match the selected filters. Submit a ticket in Intake Simulator."}
              </div>
            ) : (
              tickets.map((ticket) => {
                const isSelected = ticket.id === selectedTicket?.id;
                const analysis = ticket.analyses[0];
                return (
                  <button
                    key={ticket.id}
                    type="button"
                    onClick={() => onSelectTicket(ticket.id)}
                    className={`w-full px-4 py-3 text-left transition ${
                      isSelected
                        ? "border-l-4 border-l-blue-600 bg-blue-50/50"
                        : "border-l-4 border-l-transparent hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={`rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold ${
                          STATUS_STYLES[ticket.status].className
                        }`}
                      >
                        {STATUS_STYLES[ticket.status].label}
                      </span>

                      <div className="flex items-center gap-1.5">
                        {analysis?.injection_detected && (
                          <span
                            title="Prompt injection detected"
                            className="inline-flex items-center rounded bg-red-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-red-700"
                          >
                            <ShieldAlert className="mr-1 h-3 w-3" />
                            INJ
                          </span>
                        )}
                        {ticket.priority && (
                          <span
                            className={`rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold ${
                              PRIORITY_STYLES[ticket.priority].className
                            }`}
                          >
                            {PRIORITY_STYLES[ticket.priority].label}
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="mt-1.5 line-clamp-1 text-sm font-semibold text-slate-900">
                      {ticket.subject}
                    </p>

                    <div className="mt-1.5 flex items-center justify-between gap-2 text-xs text-slate-500">
                      <span className="truncate">
                        {ticket.customer_email || ticket.source}
                      </span>
                      <span className="shrink-0 font-mono text-[11px] text-slate-400">
                        {formatCategory(ticket.category)}
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="space-y-4 xl:col-span-8">
          {!selectedTicket ? (
            <div className="flex min-h-[420px] items-center justify-center rounded-xl border border-slate-200 bg-white p-8 text-sm text-slate-500 shadow-sm">
              Select a ticket from the queue to inspect AI triage analysis and approve outbound routing.
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded border px-2 py-0.5 font-mono text-[11px] font-semibold ${
                          STATUS_STYLES[selectedTicket.status].className
                        }`}
                      >
                        {STATUS_STYLES[selectedTicket.status].label}
                      </span>
                      <span className="font-mono text-xs text-slate-400">
                        {selectedTicket.id}
                      </span>
                    </div>
                    <h3 className="mt-2 font-display text-xl font-bold text-slate-900">
                      {selectedTicket.subject}
                    </h3>
                    <p className="mt-1 text-xs text-slate-500">
                      From{" "}
                      <span className="font-medium text-slate-700">
                        {selectedTicket.customer_name || "Unknown"}
                      </span>{" "}
                      ({selectedTicket.customer_email || "no email"}) &bull; source{" "}
                      <code className="font-mono">{selectedTicket.source}</code> &bull;{" "}
                      {formatTimestamp(selectedTicket.created_at)}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={handleAnalyze}
                    disabled={busyAction !== null}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-blue-600 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 transition hover:bg-blue-100 disabled:opacity-60"
                  >
                    <Bot className="h-3.5 w-3.5" />
                    {busyAction === "analyze" ? "Running Triage..." : "Run / Re-run AI Triage"}
                  </button>
                </div>

                {/* Live Pipeline Trace */}
                <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5">
                  {pipelineStages.map((stage) => {
                    const baseClass = !stage.active
                      ? "border-slate-200 bg-slate-50 text-slate-400"
                      : stage.tone === "danger"
                        ? "border-red-200 bg-red-50 text-red-700"
                        : stage.tone === "warn"
                          ? "border-amber-200 bg-amber-50 text-amber-800"
                          : "border-emerald-200 bg-emerald-50 text-emerald-700";

                    return (
                      <div
                        key={stage.label}
                        className={`rounded-md border px-2.5 py-1.5 font-mono text-[11px] font-semibold ${baseClass}`}
                      >
                        {stage.label}
                      </div>
                    );
                  })}
                </div>

                <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3.5">
                  <span className="mb-1 block font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    Customer Inquiry Payload
                  </span>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                    {selectedTicket.body}
                  </p>
                </div>
              </div>

              {/* AI Triage Telemetry & Security Guard */}
              {latestAnalysis && (
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                    <div className="flex items-center gap-2">
                      <Activity className="h-4 w-4 text-blue-600" />
                      <h4 className="font-display text-sm font-semibold text-slate-900">
                        AI Triage Telemetry &amp; RAG Grounding
                      </h4>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] text-slate-600">
                      <span className="rounded bg-slate-100 px-2 py-0.5">
                        {latestAnalysis.provider} / {latestAnalysis.model}
                      </span>
                      {latestAnalysis.fallback_used && (
                        <span className="rounded bg-amber-100 px-2 py-0.5 text-amber-800">
                          FALLBACK
                        </span>
                      )}
                    </div>
                  </div>

                  {latestAnalysis.injection_detected && (
                    <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
                      <div className="flex items-center gap-1.5 font-semibold">
                        <ShieldAlert className="h-4 w-4 text-red-600" />
                        Prompt Injection Alert — Risk Score{" "}
                        {formatPercent(latestAnalysis.injection_risk_score)}
                      </div>
                      <p className="mt-1 font-mono text-[11px] text-red-700">
                        Matched rules:{" "}
                        {latestAnalysis.injection_patterns.join(", ") || "untrusted directive"}
                      </p>
                    </div>
                  )}

                  {latestAnalysis.needs_human_review && !latestAnalysis.injection_detected && (
                    <div className="mt-3 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
                      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                      Flagged for human operator review before outbound dispatch.
                    </div>
                  )}

                  <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <div className="rounded-lg border border-slate-200 p-2.5">
                      <span className="block font-mono text-[10px] uppercase text-slate-400">
                        Confidence
                      </span>
                      <span className="mt-0.5 block font-mono text-base font-bold tabular-nums text-slate-900">
                        {formatPercent(latestAnalysis.confidence)}
                      </span>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-2.5">
                      <span className="block font-mono text-[10px] uppercase text-slate-400">
                        Latency
                      </span>
                      <span className="mt-0.5 flex items-center gap-1 font-mono text-base font-bold tabular-nums text-slate-900">
                        <Clock className="h-3.5 w-3.5 text-slate-400" />
                        {latestAnalysis.latency_ms.toFixed(1)} ms
                      </span>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-2.5">
                      <span className="block font-mono text-[10px] uppercase text-slate-400">
                        Repair Loops
                      </span>
                      <span className="mt-0.5 block font-mono text-base font-bold tabular-nums text-slate-900">
                        {latestAnalysis.repair_attempts}
                      </span>
                    </div>
                    <div className="rounded-lg border border-slate-200 p-2.5">
                      <span className="block font-mono text-[10px] uppercase text-slate-400">
                        KB Citations
                      </span>
                      <span className="mt-0.5 block font-mono text-base font-bold tabular-nums text-slate-900">
                        {latestAnalysis.cited_kb_ids.length}
                      </span>
                    </div>
                  </div>

                  <div className="mt-3 space-y-2">
                    <p className="text-sm text-slate-700">
                      <span className="font-semibold text-slate-900">Summary: </span>
                      {latestAnalysis.summary}
                    </p>

                    {latestAnalysis.cited_kb_ids.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="font-mono text-[11px] font-semibold text-slate-500">
                          CITED KB:
                        </span>
                        {latestAnalysis.cited_kb_ids.map((slug) => (
                          <span
                            key={slug}
                            className="rounded border border-blue-200 bg-blue-50 px-2 py-0.5 font-mono text-[11px] text-blue-700"
                          >
                            {slug}
                          </span>
                        ))}
                      </div>
                    )}

                    <button
                      type="button"
                      onClick={() => setShowReasoning((prev) => !prev)}
                      className="inline-flex items-center gap-1 font-mono text-xs font-medium text-slate-500 hover:text-slate-800"
                    >
                      {showReasoning ? (
                        <ChevronDown className="h-3.5 w-3.5" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5" />
                      )}
                      {showReasoning ? "Hide model reasoning" : "Inspect model reasoning"}
                    </button>

                    {showReasoning && (
                      <p className="rounded-lg border border-slate-200 bg-slate-50 p-3 font-mono text-xs leading-relaxed text-slate-700">
                        {latestAnalysis.reasoning}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Operator Override & Approval Form */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h4 className="font-display text-sm font-semibold text-slate-900">
                  Operator Decision &amp; Draft Response
                </h4>

                <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div>
                    <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Category
                    </label>
                    <select
                      value={editCategory}
                      onChange={(e) => setEditCategory(e.target.value as TicketCategory)}
                      className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900"
                    >
                      {CATEGORY_OPTIONS.map((cat) => (
                        <option key={cat} value={cat}>
                          {formatCategory(cat)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Priority
                    </label>
                    <select
                      value={editPriority}
                      onChange={(e) => setEditPriority(e.target.value as TicketPriority)}
                      className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900"
                    >
                      {PRIORITY_OPTIONS.map((prio) => (
                        <option key={prio} value={prio}>
                          {prio}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Assigned Team
                    </label>
                    <select
                      value={editTeam}
                      onChange={(e) => setEditTeam(e.target.value)}
                      className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 font-mono text-xs text-slate-900"
                    >
                      {ASSIGNED_TEAM_OPTIONS.map((team) => (
                        <option key={team} value={team}>
                          {team}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="mt-3">
                  <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Draft Customer Reply
                  </label>
                  <textarea
                    rows={5}
                    value={editDraftReply}
                    onChange={(e) => setEditDraftReply(e.target.value)}
                    placeholder="Edit the AI-generated draft reply before approving..."
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm leading-relaxed text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15"
                  />
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-end gap-2.5">
                  <button
                    type="button"
                    onClick={handleSaveEdits}
                    disabled={busyAction !== null}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                  >
                    <Save className="h-3.5 w-3.5" />
                    {busyAction === "save" ? "Saving..." : "Save Edits"}
                  </button>

                  <button
                    type="button"
                    onClick={handleApproveAndRoute}
                    disabled={busyAction !== null}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-60"
                  >
                    <Send className="h-3.5 w-3.5" />
                    {busyAction === "approve"
                      ? "Dispatching..."
                      : "Approve & Route Integrations"}
                  </button>
                </div>
              </div>

              {/* Outbound Delivery Audit Logs */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <Webhook className="h-4 w-4 text-slate-700" />
                    <h4 className="font-display text-sm font-semibold text-slate-900">
                      Outbound Delivery Audit Log ({selectedTicket.delivery_logs.length})
                    </h4>
                  </div>
                  <span className="font-mono text-[11px] text-slate-400">
                    HMAC-SHA256 Webhook &amp; Google Sheets
                  </span>
                </div>

                {selectedTicket.delivery_logs.length === 0 ? (
                  <p className="mt-3 text-xs text-slate-500">
                    No outbound integrations dispatched yet. Click{" "}
                    <strong>Approve &amp; Route Integrations</strong> above to trigger HMAC webhook + Google Sheets export.
                  </p>
                ) : (
                  <div className="mt-3 space-y-2">
                    {selectedTicket.delivery_logs.map((log) => {
                      const isExpanded = Boolean(expandedLogIds[log.id]);
                      return (
                        <div
                          key={log.id}
                          className="rounded-lg border border-slate-200 bg-slate-50/70"
                        >
                          <button
                            type="button"
                            onClick={() => toggleLogExpand(log.id)}
                            className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left"
                          >
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-mono text-xs font-semibold text-slate-900">
                                {log.target}
                              </span>
                              <span
                                className={`rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold ${
                                  DELIVERY_STATUS_STYLES[log.status].className
                                }`}
                              >
                                {DELIVERY_STATUS_STYLES[log.status].label}
                              </span>
                              {log.status_code !== null && (
                                <span className="font-mono text-[11px] text-slate-500">
                                  HTTP {log.status_code}
                                </span>
                              )}
                              <span className="truncate font-mono text-[11px] text-slate-500">
                                {log.endpoint}
                              </span>
                            </div>
                            <span className="font-mono text-[11px] text-slate-400">
                              {isExpanded ? "Hide JSON" : "Inspect Payload"}
                            </span>
                          </button>

                          {isExpanded && (
                            <div className="border-t border-slate-200 bg-slate-950 p-3 font-mono text-[11px] text-slate-100">
                              <pre className="overflow-x-auto whitespace-pre-wrap">
                                {JSON.stringify(
                                  {
                                    status: log.status,
                                    attempt: log.attempt,
                                    response_body: log.response_body,
                                    error_message: log.error_message,
                                    request_payload: log.request_payload,
                                  },
                                  null,
                                  2,
                                )}
                              </pre>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
