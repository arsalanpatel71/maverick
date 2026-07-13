import { useRef, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { Agent, PageMeta } from "../types";
import ShareModal from "../components/ShareModal";
import Spinner from "../components/Spinner";
import Input from "../components/Input";
import Pagination from "../components/Pagination";
import { PROVIDER_COLOR, PROVIDER_FALLBACK } from "../utils/providers";
import { useClickOutside } from "../hooks/useClickOutside";
import { useDebounce } from "../hooks/useDebounce";

type MenuAction = { agentId: string; agentName: string } | null;

function DotsIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5">
      <circle cx="2" cy="8" r="1.5" />
      <circle cx="8" cy="8" r="1.5" />
      <circle cx="14" cy="8" r="1.5" />
    </svg>
  );
}

function CardMenu({
  agent,
  onClose,
  onDelete,
  onShare,
  onClone,
}: {
  agent: Agent;
  onClose: () => void;
  onDelete: () => void;
  onShare: () => void;
  onClone: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, onClose);

  const item = "flex items-center gap-2.5 w-full px-3 py-2 text-xs text-left rounded-lg transition-colors";

  return (
    <div
      ref={ref}
      className="absolute right-0 top-8 z-20 bg-surface border border-border rounded-xl shadow-lg py-1.5 w-40 min-w-max"
      onClick={e => e.stopPropagation()}
    >
      <Link
        to={`/agents/${agent.id}`}
        className={`${item} text-slate-700 hover:bg-bg`}
        onClick={onClose}
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5"><circle cx="8" cy="8" r="6"/><path d="M8 5v3l2 2"/></svg>
        View Agent
      </Link>
      <button onClick={onShare} className={`${item} text-slate-700 hover:bg-bg`}>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5"><circle cx="13" cy="3" r="1.5"/><circle cx="3" cy="8" r="1.5"/><circle cx="13" cy="13" r="1.5"/><path d="M4.5 7l7-3.5M4.5 9l7 3.5"/></svg>
        Share
      </button>
      <button onClick={onClone} className={`${item} text-slate-700 hover:bg-bg`}>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5"><rect x="5" y="5" width="8" height="8" rx="1.5"/><path d="M3 11V3h8"/></svg>
        Clone Agent
      </button>
      <div className="h-px bg-border mx-2 my-1" />
      <button onClick={onDelete} className={`${item} text-red-500 hover:bg-red-50`}>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5"><path d="M2.5 4h11M6 4V2.5h4V4M5 4l.5 9h5l.5-9"/></svg>
        Delete
      </button>
    </div>
  );
}

function AgentCard({
  agent,
  index,
  onDelete,
  onClone,
}: {
  agent: Agent;
  index: number;
  onDelete: (id: string) => void;
  onClone: (clone: Agent) => void;
}) {
  const providerStyle = PROVIDER_COLOR[agent.provider] ?? PROVIDER_FALLBACK;
  const [menuOpen, setMenuOpen] = useState(false);
  const [shareTarget, setShareTarget] = useState<MenuAction>(null);
  const [deleting, setDeleting] = useState(false);
  const [cloning, setCloning] = useState(false);

  async function handleDelete() {
    setMenuOpen(false);
    if (!confirm(`Delete "${agent.name || agent.role}"? This cannot be undone.`)) return;
    setDeleting(true);
    try { await api.deleteAgent(agent.id); onDelete(agent.id); }
    catch { setDeleting(false); }
  }

  async function handleClone() {
    setMenuOpen(false);
    setCloning(true);
    try {
      const clone = await api.cloneAgent(agent.id);
      onClone(clone);
    } finally { setCloning(false); }
  }

  return (
    <>
      <div
        className={`bg-surface border border-border rounded-xl p-5 hover:border-accent-light hover:shadow-card transition-all duration-200 group h-full flex flex-col relative animate-fade-up ${deleting || cloning ? "opacity-50 pointer-events-none" : ""}`}
        style={{ animationDelay: `${index * 60}ms` }}
      >
        <div className="flex items-start justify-between mb-3">
          <Link to={`/agents/${agent.id}`} className="w-10 h-10 rounded-lg bg-accent-faint border border-accent-light/40 flex items-center justify-center text-lg flex-shrink-0">
            🤖
          </Link>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${providerStyle}`}>
              {agent.provider}
            </span>
            <div className="relative">
              <button
                onClick={e => { e.preventDefault(); e.stopPropagation(); setMenuOpen(o => !o); }}
                className="w-7 h-7 flex items-center justify-center rounded-lg text-muted hover:text-slate-700 hover:bg-bg border border-transparent hover:border-border transition-all"
                title="More options"
              >
                {cloning ? <span className="text-xs">…</span> : <DotsIcon />}
              </button>
              {menuOpen && (
                <CardMenu
                  agent={agent}
                  onClose={() => setMenuOpen(false)}
                  onDelete={handleDelete}
                  onShare={() => { setMenuOpen(false); setShareTarget({ agentId: agent.id, agentName: agent.name || agent.role }); }}
                  onClone={handleClone}
                />
              )}
            </div>
          </div>
        </div>

        <Link to={`/agents/${agent.id}`} className="flex-1 flex flex-col min-w-0">
          <h3 className="text-slate-900 font-semibold text-sm mb-0.5 group-hover:text-accent transition-colors line-clamp-1">
            {agent.name || agent.role}
          </h3>
          <p className="text-muted text-[11px] mb-1 line-clamp-1">{agent.role}</p>
          <p className="text-muted text-xs leading-relaxed line-clamp-2 mb-4 flex-1">{agent.goal}</p>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs px-2 py-0.5 rounded bg-bg border border-border text-slate-500 font-mono">{agent.model}</span>
            {agent.memory_enabled && (
              <span className="text-xs px-2 py-0.5 rounded bg-purple-50 border border-purple-200 text-purple-600">memory</span>
            )}
            {agent.rag_config && (
              <span className="text-xs px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-600">
                RAG ×{agent.rag_config.rag_ids.length}
              </span>
            )}
            {agent.managed_agents?.length > 0 && (
              <span className="text-xs px-2 py-0.5 rounded bg-indigo-50 border border-indigo-200 text-indigo-600">
                manager ×{agent.managed_agents.length}
              </span>
            )}
          </div>
        </Link>
      </div>

      {shareTarget && (
        <ShareModal
          resourceType="agent"
          resourceId={shareTarget.agentId}
          resourceName={shareTarget.agentName}
          onClose={() => setShareTarget(null)}
        />
      )}
    </>
  );
}

export default function Agents() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [meta, setMeta] = useState<PageMeta>({ total: 0, page: 1, page_size: 20, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const q = useDebounce(search, 300);

  useEffect(() => { setPage(1); }, [q]);

  useEffect(() => {
    setLoading(true);
    api.listAgents(q || undefined, page)
      .then((res) => { setAgents(res.items); setMeta(res.meta); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [q, page]);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="border-b border-border px-8 py-4 flex items-center gap-4 flex-shrink-0 bg-surface">
        <div className="flex-shrink-0">
          <h1 className="text-slate-900 font-semibold text-lg">Agents</h1>
          {!loading && !error && (
            <p className="text-muted text-xs mt-0.5">
              {meta.total} agent{meta.total !== 1 ? "s" : ""}{q ? " found" : " configured"}
            </p>
          )}
        </div>
        <div className="flex-1 max-w-xs">
          <Input
            size="sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agents…"
          />
        </div>
        <button
          onClick={() => navigate("/agents/new")}
          className="flex-shrink-0 flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-muted text-white rounded-lg text-sm font-medium transition-colors"
        >
          <span className="text-base leading-none">+</span>
          Add Agent
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin px-8 py-6">
        {loading && (
          <div className="flex items-center justify-center py-24 text-muted">
            <div className="flex flex-col items-center gap-3">
              <Spinner />
              <span className="text-sm">Loading agents…</span>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-600 text-sm">
            Failed to load agents: {error}
          </div>
        )}

        {!loading && !error && meta.total === 0 && !q && (
          <div className="flex flex-col items-center justify-center py-24 text-muted gap-4">
            <div className="w-16 h-16 rounded-2xl bg-accent-faint border border-accent-light/40 flex items-center justify-center text-3xl">🤖</div>
            <div className="text-center">
              <p className="text-slate-700 font-medium text-sm mb-1">No agents yet</p>
              <p className="text-xs text-muted mb-4">Create your first agent to get started.</p>
              <button
                onClick={() => navigate("/agents/new")}
                className="px-4 py-2 bg-accent hover:bg-accent-muted text-white rounded-lg text-sm font-medium transition-colors"
              >
                Create your first agent →
              </button>
            </div>
          </div>
        )}

        {!loading && !error && agents.length === 0 && q && (
          <div className="flex flex-col items-center justify-center py-24 gap-2">
            <p className="text-slate-700 font-medium text-sm">No results for "{q}"</p>
            <button onClick={() => setSearch("")} className="text-xs text-accent hover:underline">Clear search</button>
          </div>
        )}

        {!loading && !error && agents.length > 0 && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.map((a, i) => (
                <AgentCard
                  key={a.id}
                  agent={a}
                  index={i}
                  onDelete={(id) => setAgents(prev => prev.filter(x => x.id !== id))}
                  onClone={(clone) => setAgents(prev => [clone, ...prev])}
                />
              ))}
            </div>
            <Pagination meta={meta} onChange={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
