import { useRef, useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { PageMeta, RAGItem } from "../types";
import ShareModal from "../components/ShareModal";
import Input from "../components/Input";
import Spinner from "../components/Spinner";
import Pagination from "../components/Pagination";
import { PROVIDER_COLOR, PROVIDER_FALLBACK } from "../utils/providers";
import { useClickOutside } from "../hooks/useClickOutside";
import { useDebounce } from "../hooks/useDebounce";

function DotsIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5">
      <circle cx="2" cy="8" r="1.5" />
      <circle cx="8" cy="8" r="1.5" />
      <circle cx="14" cy="8" r="1.5" />
    </svg>
  );
}

function RAGCardMenu({
  rag,
  onClose,
  onDelete,
  onShare,
}: {
  rag: RAGItem;
  onClose: () => void;
  onDelete: () => void;
  onShare: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, onClose);

  const item = "flex items-center gap-2.5 w-full px-3 py-2 text-xs text-left rounded-lg transition-colors";

  return (
    <div
      ref={ref}
      className="absolute right-0 top-8 z-20 bg-surface border border-border rounded-xl shadow-lg py-1.5 w-40"
      onClick={e => e.stopPropagation()}
    >
      <Link
        to={`/rags/${rag.id}`}
        className={`${item} text-slate-700 hover:bg-bg`}
        onClick={onClose}
      >
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5"><circle cx="8" cy="8" r="6"/><path d="M8 5v3l2 2"/></svg>
        View RAG
      </Link>
      <button onClick={onShare} className={`${item} text-slate-700 hover:bg-bg`}>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5"><circle cx="13" cy="3" r="1.5"/><circle cx="3" cy="8" r="1.5"/><circle cx="13" cy="13" r="1.5"/><path d="M4.5 7l7-3.5M4.5 9l7 3.5"/></svg>
        Share
      </button>
      <div className="h-px bg-border mx-2 my-1" />
      <button onClick={onDelete} className={`${item} text-red-500 hover:bg-red-50`}>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5"><path d="M2.5 4h11M6 4V2.5h4V4M5 4l.5 9h5l.5-9"/></svg>
        Delete
      </button>
    </div>
  );
}

function RAGCard({ rag, onDelete }: { rag: RAGItem; onDelete: (id: string) => void }) {
  const providerStyle = PROVIDER_COLOR[rag.embedding_provider] ?? PROVIDER_FALLBACK;
  const [menuOpen, setMenuOpen] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setMenuOpen(false);
    if (!confirm(`Delete "${rag.name}"? This will remove all documents. This cannot be undone.`)) return;
    setDeleting(true);
    try { await api.deleteRag(rag.id); onDelete(rag.id); }
    catch { setDeleting(false); }
  }

  return (
    <>
      <div className={`bg-surface border border-border rounded-xl p-5 hover:border-accent-light hover:shadow-card transition-all group relative ${deleting ? "opacity-50 pointer-events-none" : ""}`}>
        <div className="flex items-start justify-between mb-3">
          <Link to={`/rags/${rag.id}`} className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-lg flex-shrink-0">
            📚
          </Link>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${providerStyle}`}>
              {rag.embedding_provider}
            </span>
            <div className="relative">
              <button
                onClick={e => { e.preventDefault(); e.stopPropagation(); setMenuOpen(o => !o); }}
                className="w-7 h-7 flex items-center justify-center rounded-lg text-muted hover:text-slate-700 hover:bg-bg border border-transparent hover:border-border transition-all"
                title="More options"
              >
                <DotsIcon />
              </button>
              {menuOpen && (
                <RAGCardMenu
                  rag={rag}
                  onClose={() => setMenuOpen(false)}
                  onDelete={handleDelete}
                  onShare={() => { setMenuOpen(false); setSharing(true); }}
                />
              )}
            </div>
          </div>
        </div>

        <Link to={`/rags/${rag.id}`} className="block">
          <h3 className="text-slate-900 font-semibold text-sm mb-1 group-hover:text-accent transition-colors line-clamp-1">
            {rag.name}
          </h3>
          <p className="text-muted text-xs leading-relaxed line-clamp-2 mb-4 min-h-[2.5rem]">
            {rag.description ?? "No description provided."}
          </p>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs px-2 py-0.5 rounded bg-bg border border-border text-slate-500 font-mono">{rag.embedding_model}</span>
            <span className="text-xs px-2 py-0.5 rounded bg-bg border border-border text-slate-400">{rag.embedding_dimensions}d</span>
          </div>

          <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
            <span className="text-[10px] text-muted font-mono truncate">{rag.id.slice(0, 12)}…</span>
            <span className="text-[10px] text-muted">{new Date(rag.created_at).toLocaleDateString()}</span>
          </div>
        </Link>
      </div>

      {sharing && (
        <ShareModal
          resourceType="rag"
          resourceId={rag.id}
          resourceName={rag.name}
          onClose={() => setSharing(false)}
        />
      )}
    </>
  );
}

export default function RAGs() {
  const navigate = useNavigate();
  const [rags, setRags] = useState<RAGItem[]>([]);
  const [meta, setMeta] = useState<PageMeta>({ total: 0, page: 1, page_size: 20, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const q = useDebounce(search, 300);

  useEffect(() => { setPage(1); }, [q]);

  useEffect(() => {
    setLoading(true);
    api.listRags(q || undefined, page)
      .then((res) => { setRags(res.items); setMeta(res.meta); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [q, page]);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="border-b border-border px-8 py-4 flex items-center gap-4 flex-shrink-0 bg-surface">
        <div className="flex-shrink-0">
          <h1 className="text-slate-900 font-semibold text-lg">RAGs</h1>
          {!loading && !error && (
            <p className="text-muted text-xs mt-0.5">
              {meta.total} knowledge base{meta.total !== 1 ? "s" : ""}{q ? " found" : ""}
            </p>
          )}
        </div>
        <div className="flex-1 max-w-xs">
          <Input
            size="sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search knowledge bases…"
          />
        </div>
        <button
          onClick={() => navigate("/rags/new")}
          className="flex-shrink-0 flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-muted text-white rounded-lg text-sm font-medium transition-colors"
        >
          <span className="text-base leading-none">+</span>
          Add RAG
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin px-8 py-6">
        {loading && (
          <div className="flex items-center justify-center py-24 text-muted">
            <div className="flex flex-col items-center gap-3">
              <Spinner />
              <span className="text-sm">Loading RAGs…</span>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-600 text-sm">
            Failed to load RAGs: {error}
          </div>
        )}

        {!loading && !error && meta.total === 0 && !q && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-3xl">📚</div>
            <div className="text-center">
              <p className="text-slate-700 font-medium text-sm mb-1">No knowledge bases yet</p>
              <p className="text-xs text-muted mb-4">Create a RAG to connect your agents to documents.</p>
              <button
                onClick={() => navigate("/rags/new")}
                className="px-4 py-2 bg-accent hover:bg-accent-muted text-white rounded-lg text-sm font-medium transition-colors"
              >
                Create your first RAG →
              </button>
            </div>
          </div>
        )}

        {!loading && !error && rags.length === 0 && q && (
          <div className="flex flex-col items-center justify-center py-24 gap-2">
            <p className="text-slate-700 font-medium text-sm">No results for "{q}"</p>
            <button onClick={() => setSearch("")} className="text-xs text-accent hover:underline">Clear search</button>
          </div>
        )}

        {!loading && !error && rags.length > 0 && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {rags.map((r) => (
                <RAGCard
                  key={r.id}
                  rag={r}
                  onDelete={(id) => setRags(prev => prev.filter(x => x.id !== id))}
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
