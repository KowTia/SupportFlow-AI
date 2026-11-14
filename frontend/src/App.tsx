import { useCallback, useEffect, useState } from "react";
import {
  BarChart3,
  BookOpen,
  Inbox,
  PlusCircle,
  Radio,
  ShieldCheck,
} from "lucide-react";

import { apiClient } from "./api/client";
import { KnowledgeBaseView } from "./components/KnowledgeBaseView";
import { MetricsDashboardView } from "./components/MetricsDashboardView";
import { SubmitTicketView } from "./components/SubmitTicketView";
import { TicketQueueView } from "./components/TicketQueueView";
import type { HealthStatus, Ticket } from "./types/api";

type ConsoleTab = "intake" | "queue" | "kb" | "metrics";

const NAV_ITEMS: {
  id: ConsoleTab;
  label: string;
  subtitle: string;
  icon: typeof PlusCircle;
}[] = [
  {
    id: "intake",
    label: "Demo Intake",
    subtitle: "Submit & Prompt Guard",
    icon: PlusCircle,
  },
  {
    id: "queue",
    label: "Ticket Queue",
    subtitle: "Approve & Route",
    icon: Inbox,
  },
  {
    id: "kb",
    label: "Knowledge Base",
    subtitle: "pgvector RAG Search",
    icon: BookOpen,
  },
  {
    id: "metrics",
    label: "Metrics",
    subtitle: "Latency & Quality",
    icon: BarChart3,
  },
];

export function App() {
  const [activeTab, setActiveTab] = useState<ConsoleTab>("intake");
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState(false);

  const checkHealth = useCallback(async () => {
    try {
      const data = await apiClient.getHealth();
      setHealth(data);
      setHealthError(false);
    } catch {
      setHealthError(true);
    }
  }, []);

  useEffect(() => {
    void checkHealth();
    const timer = window.setInterval(() => {
      void checkHealth();
    }, 30000);
    return () => window.clearInterval(timer);
  }, [checkHealth]);

  const handleTicketCreated = (ticket: Ticket) => {
    setSelectedTicketId(ticket.id);
  };

  const handleInspectTicket = (ticketId: string) => {
    setSelectedTicketId(ticketId);
    setActiveTab("queue");
  };

  return (
    <div className="min-h-screen bg-[#F6F8FC] text-slate-900 lg:flex">
      {/* Left Navigation Rail */}
      <aside className="flex w-full shrink-0 flex-col justify-between border-b border-slate-800 bg-[#0B101B] text-slate-100 lg:min-h-screen lg:w-64 lg:border-b-0 lg:border-r">
        <div>
          <div className="flex items-center gap-3 border-b border-slate-800/90 px-5 py-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h1 className="font-display text-base font-bold tracking-tight text-white">
                SupportFlow AI
              </h1>
              <p className="font-mono text-[11px] text-slate-400">
                OPERATOR CONTROL DESK
              </p>
            </div>
          </div>

          <nav className="grid grid-cols-2 gap-1.5 p-3 lg:grid-cols-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                    active
                      ? "bg-blue-600/15 text-white ring-1 ring-blue-500/40"
                      : "text-slate-400 hover:bg-slate-800/70 hover:text-slate-100"
                  }`}
                >
                  <Icon
                    className={`h-4 w-4 shrink-0 ${
                      active ? "text-blue-400" : "text-slate-500"
                    }`}
                  />
                  <div className="min-w-0">
                    <span className="block text-sm font-semibold leading-tight">
                      {item.label}
                    </span>
                    <span className="block truncate font-mono text-[10px] text-slate-400">
                      {item.subtitle}
                    </span>
                  </div>
                </button>
              );
            })}
          </nav>
        </div>

        <div className="hidden border-t border-slate-800/90 p-4 lg:block">
          <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                API Health (/healthz)
              </span>
              <Radio
                className={`h-3.5 w-3.5 ${
                  healthError
                    ? "text-red-400"
                    : health
                      ? "text-emerald-400"
                      : "text-slate-500"
                }`}
              />
            </div>

            {healthError ? (
              <p className="mt-1.5 font-mono text-xs text-red-400">
                Backend unreachable
              </p>
            ) : health ? (
              <div className="mt-1.5 space-y-0.5 font-mono text-[11px] text-slate-300">
                <p className="text-emerald-400">
                  {health.status.toUpperCase()} &bull; DB {health.database}
                </p>
                <p className="text-slate-400">
                  v{health.version} ({health.environment})
                </p>
              </div>
            ) : (
              <p className="mt-1.5 font-mono text-xs text-slate-400">
                Checking connectivity...
              </p>
            )}
          </div>
        </div>
      </aside>

      {/* Main Workspace Canvas */}
      <div className="flex-1">
        <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-6 py-3">
          <div className="flex items-center gap-2 font-mono text-xs text-slate-500">
            <span>RAG ENGINE: pgvector</span>
            <span className="text-slate-300">/</span>
            <span>REPAIR LOOP: max 2 retries</span>
            <span className="text-slate-300">/</span>
            <span>WEBHOOKS: HMAC-SHA256</span>
          </div>

          <button
            type="button"
            onClick={() => void checkHealth()}
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px] font-medium ${
              healthError
                ? "border-red-200 bg-red-50 text-red-700"
                : "border-emerald-200 bg-emerald-50 text-emerald-700"
            }`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                healthError ? "bg-red-500" : "bg-emerald-500"
              }`}
            />
            {healthError
              ? "API OFFLINE"
              : health
                ? `CONNECTED v${health.version}`
                : "CONNECTING..."}
          </button>
        </header>

        <main className="mx-auto max-w-7xl p-6">
          {activeTab === "intake" && (
            <SubmitTicketView
              onTicketCreated={handleTicketCreated}
              onInspectTicket={handleInspectTicket}
            />
          )}
          {activeTab === "queue" && (
            <TicketQueueView
              selectedTicketId={selectedTicketId}
              onSelectTicket={setSelectedTicketId}
            />
          )}
          {activeTab === "kb" && <KnowledgeBaseView />}
          {activeTab === "metrics" && <MetricsDashboardView />}
        </main>
      </div>
    </div>
  );
}

export default App;
