import { useState } from "react";
import type { RAGChunk } from "../../types";
import { fileIcon } from "../../utils/ragUtils";

interface Props {
  name: string;
  chunks: RAGChunk[];
}

export default function DocCard({ name, chunks }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null);
  const first = chunks[0];
  const icon = fileIcon(first.metadata);
  const isUrl = first.source && (first.source.startsWith("http://") || first.source.startsWith("https://"));

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden hover:border-accent-light/50 transition-colors">
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-bg border border-border flex items-center justify-center flex-shrink-0 text-base">{icon}</div>
          <div className="flex-1 min-w-0">
            <p className="text-slate-800 text-sm font-medium truncate">{name}</p>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-bg border border-border text-muted">
                {chunks.length} chunk{chunks.length !== 1 ? "s" : ""}
              </span>
              {first.source && (
                isUrl
                  ? <a href={first.source} target="_blank" rel="noreferrer" className="text-[10px] text-accent hover:underline truncate max-w-[160px]">{first.source}</a>
                  : <span className="text-[10px] text-muted truncate max-w-[160px]">{first.source}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className="type-caption">{new Date(first.created_at).toLocaleDateString()}</span>
            <button onClick={() => setExpanded(p => !p)} className="text-muted hover:text-slate-600 text-xs transition-colors">
              {expanded ? "▲" : "▼"}
            </button>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-border divide-y divide-border">
          {chunks.map((c, i) => (
            <div key={c.id} className="px-4 py-3">
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <span className="type-caption font-mono">chunk {i + 1}/{chunks.length}</span>
                <button onClick={() => setExpandedChunk(expandedChunk === c.id ? null : c.id)}
                  className="text-[10px] text-accent hover:underline flex-shrink-0">
                  {expandedChunk === c.id ? "collapse" : "expand"}
                </button>
              </div>
              <p className={`text-xs text-slate-600 leading-relaxed font-mono ${expandedChunk === c.id ? "" : "line-clamp-2"}`}>{c.data}</p>
              <p className="type-caption mt-1 font-mono">{c.data.length} chars</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
