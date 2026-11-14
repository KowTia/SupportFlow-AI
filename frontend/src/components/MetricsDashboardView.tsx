import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Clock,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Webhook,
  Wrench,
} from "lucide-react";

import { apiClient, ApiError } from "../api/client";
import type { DashboardMetrics } from "../types/api";
import { formatCategory, formatPercent } from "../utils/format";

function BreakdownCard({
  title,
  entries,
  total,
  barClass,
}: {
  title: string;
  entries: Record<string, number>;
  total: number;
  barClass: string;
}) {
  const sorted = Object.entries(entries).sort((a, b) => b[1] - a[1]);
  const denominator = total > 0 ? total : 1;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="font-display text-sm font-semibold text-slate-900">{title}</h3>
      {sorted.length === 0 ? (
        <p className="mt-4 text-xs text-slate-400">No recorded items yet.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {sorted.map(([label, count]) => {
            const pct = Math.min(100, Math.round((count / denominator) * 100));
            return (
              <div key={label}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="font-mono font-medium uppercase text-slate-700">
                    {formatCategory(label)}
                  </span>
                  <span className="font-mono font-semibold tabular-nums text-slate-900">
                    {count} <span className="text-slate-400">({pct}%)</span>
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full ${barClass}`}
                    style={{ width: `${Math.max(4, pct)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function MetricsDashboardView() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getMetrics();
      setMetrics(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMetrics();
  }, [loadMetrics]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-mono text-xs font-medium uppercase tracking-wider text-blue-600">
            04 // Operational Telemetry &amp; AI Reliability
          </p>
          <h2 className="mt-1 font-display text-2xl font-bold tracking-tight text-slate-900">
            Pipeline &amp; Quality Metrics
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Live aggregates from PostgreSQL across ticket intake, LLM repair loops, prompt security, and outbound routing.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void loadMetrics()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 self-start rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Telemetry
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {metrics && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Total Tickets
                </span>
                <BarChart3 className="h-4 w-4 text-blue-600" />
              </div>
              <p className="mt-2 font-display text-3xl font-bold tabular-nums text-slate-900">
                {metrics.total_tickets}
              </p>
              <p className="mt-1 font-mono text-xs text-slate-500">
                {metrics.total_analyses} persisted AI analysis run(s)
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Avg Confidence
                </span>
                <Sparkles className="h-4 w-4 text-emerald-600" />
              </div>
              <p className="mt-2 font-display text-3xl font-bold tabular-nums text-slate-900">
                {formatPercent(metrics.avg_confidence)}
              </p>
              <p className="mt-1 font-mono text-xs text-slate-500">
                Human review rate: {formatPercent(metrics.human_review_rate)}
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Avg Triage Latency
                </span>
                <Clock className="h-4 w-4 text-slate-600" />
              </div>
              <p className="mt-2 font-display text-3xl font-bold tabular-nums text-slate-900">
                {metrics.avg_latency_ms.toFixed(1)}{" "}
                <span className="text-lg font-medium text-slate-400">ms</span>
              </p>
              <p className="mt-1 font-mono text-xs text-slate-500">
                End-to-end RAG + LLM structured output
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Prompt Injections Caught
                </span>
                <ShieldAlert className="h-4 w-4 text-red-600" />
              </div>
              <p className="mt-2 font-display text-3xl font-bold tabular-nums text-red-600">
                {metrics.injection_detected_count}
              </p>
              <p className="mt-1 font-mono text-xs text-slate-500">
                Quarantined to awaiting_review before routing
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Schema Repair Loops
                </span>
                <Wrench className="h-4 w-4 text-amber-600" />
              </div>
              <p className="mt-2 font-display text-3xl font-bold tabular-nums text-slate-900">
                {metrics.total_repair_attempts}
              </p>
              <p className="mt-1 font-mono text-xs text-slate-500">
                Auto-repaired malformed JSON responses
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Outbound Dispatches
                </span>
                <Webhook className="h-4 w-4 text-blue-600" />
              </div>
              <p className="mt-2 font-display text-3xl font-bold tabular-nums text-slate-900">
                {metrics.total_deliveries}
              </p>
              <p className="mt-1 font-mono text-xs text-slate-500">
                HMAC webhooks &amp; Google Sheets rows
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <BreakdownCard
              title="Tickets by Workflow Status"
              entries={metrics.tickets_by_status}
              total={metrics.total_tickets}
              barClass="bg-blue-600"
            />
            <BreakdownCard
              title="Tickets by Category"
              entries={metrics.tickets_by_category}
              total={metrics.total_tickets}
              barClass="bg-slate-800"
            />
            <BreakdownCard
              title="Tickets by Priority"
              entries={metrics.tickets_by_priority}
              total={metrics.total_tickets}
              barClass="bg-amber-500"
            />
            <div className="space-y-5">
              <BreakdownCard
                title="Outbound Deliveries by Target"
                entries={metrics.deliveries_by_target}
                total={metrics.total_deliveries}
                barClass="bg-emerald-600"
              />
              <BreakdownCard
                title="Outbound Deliveries by Status"
                entries={metrics.deliveries_by_status}
                total={metrics.total_deliveries}
                barClass="bg-indigo-600"
              />
            </div>
          </div>
        </>
      )}

      {!metrics && loading && (
        <div className="flex items-center justify-center rounded-xl border border-slate-200 bg-white p-12 text-sm text-slate-500">
          <Activity className="mr-2 h-4 w-4 animate-pulse text-blue-600" />
          Loading operational telemetry...
        </div>
      )}
    </div>
  );
}
