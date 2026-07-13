import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { RAGChunk, RAGChunkResult, RAGItem } from "../types";
import Select from "../components/Select";
import Spinner from "../components/Spinner";
import AddTextModal from "../components/rag/AddTextModal";
import AddFileModal from "../components/rag/AddFileModal";
import DocCard from "../components/rag/DocCard";
import ResultCard from "../components/rag/ResultCard";
import { groupByName } from "../utils/ragUtils";

const RETRIEVAL_TYPES = [
  { value: "basic",      label: "Basic — vector cosine similarity" },
  { value: "mmr",        label: "MMR — relevance + diversity" },
  { value: "hyde",       label: "HyDE — hypothetical doc embedding" },
  { value: "time_aware", label: "Time-aware — recency weighted" },
];

interface QueryConfig {
  top_k: number;
  retrieval_type: string;
  score_threshold: number;
  lambda_param: number;
  time_decay_factor: number;
}

export default function RAGPage() {
  const { ragId } = useParams<{ ragId: string }>();
  const navigate = useNavigate();

  const [rag, setRag]         = useState<RAGItem | null>(null);
  const [chunks, setChunks]   = useState<RAGChunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddText, setShowAddText] = useState(false);
  const [showAddFile, setShowAddFile] = useState(false);

  const [query, setQuery]     = useState("");
  const [config, setConfig]   = useState<QueryConfig>({
    top_k: 5, retrieval_type: "basic", score_threshold: 0, lambda_param: 0.6, time_decay_factor: 0.7,
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [querying, setQuerying]         = useState(false);
  const [results, setResults]           = useState<RAGChunkResult[] | null>(null);
  const [totalFound, setTotalFound]     = useState(0);
  const [queryError, setQueryError]     = useState<string | null>(null);

  function loadChunks() {
    if (!ragId) return;
    api.listChunks(ragId).then(setChunks).catch(() => {});
  }

  useEffect(() => {
    if (!ragId) return;
    Promise.all([api.getRag(ragId), api.listChunks(ragId)])
      .then(([r, c]) => { setRag(r); setChunks(c); })
      .catch(() => setRag(null))
      .finally(() => setLoading(false));
  }, [ragId]);

  async function handleQuery() {
    if (!query.trim() || !ragId) return;
    setQuerying(true); setQueryError(null); setResults(null);
    try {
      const res = await api.queryRag(ragId, {
        query: query.trim(), top_k: config.top_k, retrieval_type: config.retrieval_type,
        score_threshold: config.score_threshold, lambda_param: config.lambda_param,
        time_decay_factor: config.time_decay_factor,
      });
      setResults(res.chunks);
      setTotalFound(res.total_found);
    } catch (e: unknown) { setQueryError(e instanceof Error ? e.message : "Query failed"); }
    finally { setQuerying(false); }
  }

  const docs = groupByName(chunks);
  const docCount = docs.size;
  const chunkCount = chunks.length;

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-muted">
        <div className="flex flex-col items-center gap-3">
          <Spinner />
          <span className="text-sm">Loading…</span>
        </div>
      </div>
    );
  }

  if (!rag) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted text-sm mb-4">RAG not found.</p>
          <button onClick={() => navigate("/rags")} className="text-accent text-sm hover:underline">← Back to RAGs</button>
        </div>
      </div>
    );
  }

  return (
    <>
      {showAddText && ragId && <AddTextModal ragId={ragId} onDone={loadChunks} onClose={() => setShowAddText(false)} />}
      {showAddFile && ragId && <AddFileModal ragId={ragId} onDone={loadChunks} onClose={() => setShowAddFile(false)} />}

      <div className="h-full flex flex-col">
        <div className="border-b border-border px-6 py-3.5 flex items-center gap-3 flex-shrink-0 bg-surface">
          <button onClick={() => navigate("/rags")} className="text-muted hover:text-slate-700 transition-colors text-sm">← RAGs</button>
          <span className="text-border">|</span>
          <span className="text-slate-900 text-sm font-medium truncate">{rag.name}</span>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs px-2 py-0.5 rounded-full border font-medium bg-emerald-50 text-emerald-600 border-emerald-200">{rag.embedding_provider}</span>
            <span className="text-xs px-2 py-0.5 rounded bg-bg border border-border text-slate-500 font-mono">{rag.embedding_model}</span>
            <span className="type-caption hidden sm:inline font-mono">{rag.embedding_dimensions}d</span>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          <div className="flex-[6] border-r border-border flex flex-col overflow-hidden">
            <div className="px-5 py-3.5 border-b border-border flex items-center justify-between flex-shrink-0 bg-surface">
              <div>
                <span className="text-slate-800 text-sm font-medium">{docCount} document{docCount !== 1 ? "s" : ""}</span>
                <span className="text-muted text-xs ml-2">· {chunkCount} chunk{chunkCount !== 1 ? "s" : ""}</span>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setShowAddText(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-bg border border-border hover:border-accent-light/50 text-slate-600 rounded-lg text-xs font-medium transition-colors">
                  ✏ Add Text
                </button>
                <button onClick={() => setShowAddFile(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-bg border border-border hover:border-accent-light/50 text-slate-600 rounded-lg text-xs font-medium transition-colors">
                  📁 Add File
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-3">
              {docCount === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center gap-4 py-12">
                  <div className="w-14 h-14 rounded-2xl bg-accent-faint border border-accent-light/40 flex items-center justify-center text-2xl">📚</div>
                  <div>
                    <p className="text-slate-700 text-sm font-medium mb-1">No documents yet</p>
                    <p className="text-muted text-xs mb-4">Add text or upload a file to populate this knowledge base.</p>
                    <div className="flex gap-2 justify-center flex-wrap">
                      <button onClick={() => setShowAddText(true)} className="px-3 py-1.5 bg-surface border border-border hover:border-accent-light/50 text-slate-600 rounded-lg text-xs transition-colors">Add Text</button>
                      <button onClick={() => setShowAddFile(true)} className="px-3 py-1.5 bg-surface border border-border hover:border-accent-light/50 text-slate-600 rounded-lg text-xs transition-colors">Add File</button>
                    </div>
                  </div>
                </div>
              )}
              {Array.from(docs.entries()).map(([name, docChunks]) => (
                <DocCard key={name} name={name} chunks={docChunks} />
              ))}
            </div>
          </div>

          <div className="flex-[4] flex flex-col overflow-hidden min-w-0">
            <div className="px-5 py-3.5 border-b border-border flex-shrink-0 bg-surface">
              <p className="text-slate-800 text-sm font-medium">Query Playground</p>
              <p className="text-muted text-xs mt-0.5">Test retrieval against this knowledge base</p>
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-thin p-4 flex flex-col gap-4">
              <div>
                <textarea
                  value={query} onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleQuery(); }}
                  rows={4} placeholder="Ask a question or describe what you're looking for…"
                  className="w-full bg-surface border border-border rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors resize-none leading-relaxed"
                />
                <p className="type-caption mt-1">⌘/Ctrl+Enter to search</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="type-label block mb-1.5">Retrieval Type</label>
                  <Select value={config.retrieval_type} onChange={e => setConfig(c => ({ ...c, retrieval_type: e.target.value }))}>
                    {RETRIEVAL_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </Select>
                </div>
                <div>
                  <label className="type-label block mb-1.5">Top K <span className="font-mono text-accent normal-case">{config.top_k}</span></label>
                  <input type="range" min={1} max={20} value={config.top_k} onChange={e => setConfig(c => ({ ...c, top_k: parseInt(e.target.value) }))} className="w-full accent-accent mt-1" />
                  <div className="flex justify-between type-caption"><span>1</span><span>20</span></div>
                </div>
              </div>

              <button onClick={() => setShowAdvanced(p => !p)} className="text-xs text-muted hover:text-slate-600 flex items-center gap-1.5 transition-colors">
                <span>{showAdvanced ? "▲" : "▼"}</span> Advanced settings
              </button>

              {showAdvanced && (
                <div className="bg-surface border border-border rounded-xl p-4 space-y-4">
                  <div>
                    <div className="flex justify-between mb-1">
                      <label className="type-label">Score Threshold</label>
                      <span className="type-caption font-mono text-accent">{config.score_threshold}</span>
                    </div>
                    <input type="range" min={0} max={1} step={0.05} value={config.score_threshold} onChange={e => setConfig(c => ({ ...c, score_threshold: parseFloat(e.target.value) }))} className="w-full accent-accent" />
                    <div className="flex justify-between type-caption mt-0.5"><span>0</span><span>1</span></div>
                  </div>
                  {config.retrieval_type === "mmr" && (
                    <div>
                      <div className="flex justify-between mb-1">
                        <label className="type-label">Lambda</label>
                        <span className="type-caption font-mono text-accent">{config.lambda_param}</span>
                      </div>
                      <input type="range" min={0} max={1} step={0.05} value={config.lambda_param} onChange={e => setConfig(c => ({ ...c, lambda_param: parseFloat(e.target.value) }))} className="w-full accent-accent" />
                      <div className="flex justify-between type-caption mt-0.5"><span>diversity</span><span>relevance</span></div>
                    </div>
                  )}
                  {config.retrieval_type === "time_aware" && (
                    <div>
                      <div className="flex justify-between mb-1">
                        <label className="type-label">Time Decay</label>
                        <span className="type-caption font-mono text-accent">{config.time_decay_factor}</span>
                      </div>
                      <input type="range" min={0} max={1} step={0.05} value={config.time_decay_factor} onChange={e => setConfig(c => ({ ...c, time_decay_factor: parseFloat(e.target.value) }))} className="w-full accent-accent" />
                      <div className="flex justify-between type-caption mt-0.5"><span>similarity</span><span>recency</span></div>
                    </div>
                  )}
                </div>
              )}

              <button onClick={handleQuery} disabled={querying || !query.trim() || chunkCount === 0}
                className="w-full py-2.5 bg-accent hover:bg-accent-muted disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2">
                {querying ? <><Spinner size="sm" variant="white" /> Searching…</> : "Search"}
              </button>

              {queryError && <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-600 text-xs">{queryError}</div>}

              {results !== null && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-slate-600 font-medium">{totalFound} result{totalFound !== 1 ? "s" : ""} found</p>
                    <span className="type-caption">{config.retrieval_type}</span>
                  </div>
                  {results.length === 0 && (
                    <div className="bg-surface border border-border rounded-xl p-6 text-center">
                      <p className="text-muted text-sm">No chunks matched.</p>
                      <p className="type-caption mt-1">Try lowering the score threshold or changing the query.</p>
                    </div>
                  )}
                  {results.map((r, i) => <ResultCard key={r.id} chunk={r} rank={i + 1} />)}
                </div>
              )}

              {chunkCount === 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-amber-700 text-xs text-center">
                  Add documents to the knowledge base before querying.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
