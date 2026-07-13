import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

const PROVIDER_COLORS: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  anthropic:  { bg: "bg-orange-50",  text: "text-orange-600",  border: "border-orange-200",  dot: "bg-orange-400" },
  openai:     { bg: "bg-emerald-50", text: "text-emerald-600", border: "border-emerald-200", dot: "bg-emerald-400" },
  google:     { bg: "bg-blue-50",    text: "text-blue-600",    border: "border-blue-200",    dot: "bg-blue-400" },
  perplexity: { bg: "bg-purple-50",  text: "text-purple-600",  border: "border-purple-200",  dot: "bg-purple-400" },
};

function RatingBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value * 10}%` }} />
      </div>
      <span className="text-xs text-muted w-6 text-right">{value}</span>
    </div>
  );
}

function fmt(n: number) {
  return n < 0.01 ? n.toFixed(5) : n < 1 ? n.toFixed(4) : n.toFixed(2);
}

function fmtTokens(n: number): string {
  if (n < 1000) return String(n);
  return `${(n / 1000).toFixed(1)}K`;
}

function timeUntil(epochSecs: number): string {
  const diffMs = epochSecs * 1000 - Date.now();
  if (diffMs <= 0) return "soon";
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays > 1) return `${diffDays}d`;
  const diffHrs = Math.floor(diffMs / 3600000);
  if (diffHrs > 0) return `${diffHrs}h`;
  return `${Math.floor(diffMs / 60000)}m`;
}

const PERIOD_LABEL: Record<string, string> = { daily: "day", weekly: "week", monthly: "month" };

interface ModelRow {
  model_id: string; label: string; provider: string; provider_label: string;
  provider_color: string; in_per_m: number; out_per_m: number; speed: number; quality: number;
}

interface UsageData {
  total_cost_usd: number; total_input_tokens: number; total_output_tokens: number;
  by_model: { model: string; provider: string; input_tokens: number; output_tokens: number; cost_usd: number; calls: number }[];
  by_provider: { provider: string; cost_usd: number; calls: number }[];
  recent_traces: { trace_id: string; agent_id: string; model: string; provider: string; input_tokens: number; output_tokens: number; cost_usd: number; created_at: string }[];
}

const DAYS_OPTIONS = [7, 14, 30, 90];

export default function Credits() {
  const { user } = useAuth();
  const [catalog, setCatalog] = useState<ModelRow[]>([]);
  const [balance, setBalance] = useState<Record<string, number | string> | null>(null);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [activeProvider, setActiveProvider] = useState("all");
  const [days, setDays] = useState(30);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loadingUsage, setLoadingUsage] = useState(true);

  useEffect(() => {
    const calls: [Promise<unknown>, Promise<unknown>] = [
      api.modelCatalog(),
      user?.role !== "super_admin" ? api.myBalance() : Promise.resolve(null),
    ];
    Promise.all(calls)
      .then(([c, b]) => { setCatalog(c as unknown as ModelRow[]); setBalance(b as Record<string, number | string> | null); })
      .finally(() => setLoadingCatalog(false));
  }, [user]);

  useEffect(() => {
    setLoadingUsage(true);
    api.myUsage(days)
      .then(u => setUsage(u as unknown as UsageData))
      .finally(() => setLoadingUsage(false));
  }, [days]);

  const providers = ["all", ...Array.from(new Set(catalog.map(m => m.provider)))];
  const filtered = activeProvider === "all" ? catalog : catalog.filter(m => m.provider === activeProvider);

  const col = (p: string) => PROVIDER_COLORS[p] ?? { bg: "bg-slate-50", text: "text-slate-600", border: "border-slate-200", dot: "bg-slate-400" };

  return (
    <div className="h-full overflow-y-auto bg-bg">
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">

        {/* Header */}
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Credits & Usage</h1>
            <p className="text-sm text-muted mt-0.5">Track token consumption and costs across all models</p>
          </div>
          {user?.role !== "super_admin" && balance && (() => {
            const b = balance as { credits_period: string; next_reset_at: number };
            return (
              <p className="text-xs text-muted">
                <span className="capitalize">{PERIOD_LABEL[b.credits_period] ?? b.credits_period}</span> limit
                {" · "}resets in <span className="font-medium text-slate-700">{timeUntil(b.next_reset_at)}</span>
              </p>
            );
          })()}
        </div>

        {/* Summary row */}
        {usage && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-surface border border-border rounded-xl p-5">
              <p className="text-xs font-medium text-muted mb-2">Total Spent ({days}d)</p>
              <p className="text-2xl font-bold text-slate-900 font-mono tabular-nums leading-tight">
                ${fmt(usage.total_cost_usd)}
              </p>
              <p className="text-xs text-muted mt-3 font-medium">
                {usage.by_model.reduce((a, b) => a + b.calls, 0)} API calls
              </p>
            </div>

            <div className="bg-surface border border-border rounded-xl p-5">
              <p className="text-xs font-medium text-muted mb-2">Top Model ({days}d)</p>
              {(() => {
                const top = [...usage.by_model].sort((a, b) => b.calls - a.calls)[0];
                if (!top) return <p className="text-sm text-muted">No data</p>;
                const c = col(top.provider);
                return (
                  <>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${c.dot}`} />
                      <p className="text-sm font-bold text-slate-900 truncate">{top.model}</p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${c.bg} ${c.text} ${c.border}`}>
                      {top.provider}
                    </span>
                    <div className="flex justify-between mt-3 text-xs text-muted">
                      <span><span className="font-bold text-slate-800 font-mono">{top.calls}</span> calls</span>
                      <span><span className="font-bold text-slate-800 font-mono">${fmt(top.cost_usd)}</span> spent</span>
                    </div>
                  </>
                );
              })()}
            </div>
          </div>
        )}

        {/* Usage breakdown */}
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <h2 className="text-sm font-semibold text-slate-900">Usage by Model</h2>
            <div className="flex items-center gap-1 bg-bg border border-border rounded-lg p-0.5">
              {DAYS_OPTIONS.map(d => (
                <button
                  key={d}
                  onClick={() => setDays(d)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                    days === d ? "bg-surface shadow-sm text-slate-900" : "text-muted hover:text-slate-700"
                  }`}
                >
                  {d}d
                </button>
              ))}
            </div>
          </div>

          {loadingUsage ? (
            <div className="flex items-center justify-center h-24 text-muted text-sm">Loading…</div>
          ) : !usage || usage.by_model.length === 0 ? (
            <div className="flex items-center justify-center h-24 text-muted text-sm">No usage yet</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-5 py-3 text-xs font-medium text-muted">Model</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-muted">Calls</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-muted">Tokens in</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-muted">Tokens out</th>
                  <th className="text-right px-5 py-3 text-xs font-medium text-muted">Cost</th>
                </tr>
              </thead>
              <tbody>
                {usage.by_model.map(row => {
                  const c = col(row.provider);
                  return (
                    <tr key={row.model} className="border-b border-border last:border-0 hover:bg-bg/50 transition-colors">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${c.dot}`} />
                          <span className="font-medium text-slate-800">{row.model}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-slate-700 font-mono tabular-nums">{row.calls}</td>
                      <td className="px-4 py-3 text-right font-semibold text-slate-700 font-mono tabular-nums">{fmtTokens(row.input_tokens)}</td>
                      <td className="px-4 py-3 text-right font-semibold text-slate-700 font-mono tabular-nums">{fmtTokens(row.output_tokens)}</td>
                      <td className="px-5 py-3 text-right font-bold text-slate-900 font-mono tabular-nums">${fmt(row.cost_usd)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Model catalog */}
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-sm font-semibold text-slate-900 mb-3">Model Catalog</h2>
            {/* Provider filter */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {providers.map(p => {
                const c = p === "all" ? null : col(p);
                const isActive = activeProvider === p;
                return (
                  <button
                    key={p}
                    onClick={() => setActiveProvider(p)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                      isActive
                        ? c
                          ? `${c.bg} ${c.text} ${c.border}`
                          : "bg-slate-900 text-white border-slate-900"
                        : "bg-bg text-muted border-border hover:border-slate-300 hover:text-slate-700"
                    }`}
                  >
                    {p === "all" ? "All" : p.charAt(0).toUpperCase() + p.slice(1)}
                  </button>
                );
              })}
            </div>
          </div>

          {loadingCatalog ? (
            <div className="flex items-center justify-center h-24 text-muted text-sm">Loading…</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-5 py-3 text-xs font-medium text-muted">Model</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted">Provider</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted w-32">Speed</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted w-32">Quality</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-muted">$/1M in</th>
                  <th className="text-right px-5 py-3 text-xs font-medium text-muted">$/1M out</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(m => {
                  const c = col(m.provider);
                  return (
                    <tr key={m.model_id} className="border-b border-border last:border-0 hover:bg-bg/50 transition-colors">
                      <td className="px-5 py-3">
                        <span className="font-medium text-slate-800">{m.label}</span>
                        <span className="text-muted text-xs block">{m.model_id}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${c.bg} ${c.text} ${c.border}`}>
                          {m.provider_label}
                        </span>
                      </td>
                      <td className="px-4 py-3 w-32">
                        <RatingBar value={m.speed} color="bg-blue-400" />
                      </td>
                      <td className="px-4 py-3 w-32">
                        <RatingBar value={m.quality} color="bg-violet-400" />
                      </td>
                      <td className="px-4 py-3 text-right font-bold text-slate-800 font-mono tabular-nums text-xs">${m.in_per_m.toFixed(2)}</td>
                      <td className="px-5 py-3 text-right font-bold text-slate-800 font-mono tabular-nums text-xs">${m.out_per_m.toFixed(2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Recent traces */}
        {usage && usage.recent_traces.length > 0 && (
          <div className="bg-surface border border-border rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-border">
              <h2 className="text-sm font-semibold text-slate-900">Recent Calls</h2>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-5 py-3 text-xs font-medium text-muted">Model</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-muted">In</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-muted">Out</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-muted">Cost</th>
                  <th className="text-right px-5 py-3 text-xs font-medium text-muted">When</th>
                </tr>
              </thead>
              <tbody>
                {usage.recent_traces.map(t => {
                  const c = col(t.provider);
                  const when = t.created_at ? new Date(t.created_at).toLocaleString() : "—";
                  return (
                    <tr key={t.trace_id} className="border-b border-border last:border-0 hover:bg-bg/50">
                      <td className="px-5 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${c.dot}`} />
                          <span className="text-slate-800">{t.model || "—"}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-right font-semibold text-slate-700 font-mono tabular-nums text-xs">{fmtTokens(t.input_tokens)}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-slate-700 font-mono tabular-nums text-xs">{fmtTokens(t.output_tokens)}</td>
                      <td className="px-4 py-2.5 text-right font-bold text-slate-900 font-mono tabular-nums text-xs">${fmt(t.cost_usd)}</td>
                      <td className="px-5 py-2.5 text-right text-muted text-xs">{when}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {user?.role === "super_admin" && (
          <p className="text-xs text-muted text-center">
            View all-org usage in the <a href="/admin" className="text-accent hover:underline">Admin panel →</a>
          </p>
        )}
      </div>
    </div>
  );
}
