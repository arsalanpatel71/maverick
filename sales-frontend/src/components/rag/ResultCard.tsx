import { useState } from "react";
import type { RAGChunkResult } from "../../types";
import { scoreColor, scoreBg } from "../../utils/ragUtils";

interface Props {
  chunk: RAGChunkResult;
  rank: number;
}

export default function ResultCard({ chunk, rank }: Props) {
  const [expanded, setExpanded] = useState(false);
  const pct = Math.round(chunk.score * 100);

  return (
    <div className="bg-surface border border-border rounded-xl p-4 space-y-2.5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="type-caption font-mono flex-shrink-0">#{rank}</span>
          <p className="text-slate-800 text-xs font-medium truncate">{chunk.name}</p>
        </div>
        <div className={`text-[10px] px-2 py-0.5 rounded-full border font-mono font-medium flex-shrink-0 ${scoreColor(chunk.score)}`}>
          {pct}%
        </div>
      </div>

      <div className="h-1 rounded-full bg-bg overflow-hidden">
        <div className={`h-full rounded-full transition-all ${scoreBg(chunk.score)}`} style={{ width: `${pct}%` }} />
      </div>

      <p className={`text-xs text-slate-600 leading-relaxed font-mono ${expanded ? "" : "line-clamp-3"}`}>{chunk.data}</p>

      <div className="flex items-center justify-between">
        <button onClick={() => setExpanded(p => !p)} className="text-[10px] text-accent hover:underline transition-colors">
          {expanded ? "Show less" : "Show full chunk"}
        </button>
        {chunk.source && <span className="type-caption truncate max-w-[140px]">{chunk.source}</span>}
      </div>
    </div>
  );
}
