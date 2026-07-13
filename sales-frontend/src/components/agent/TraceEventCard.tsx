import { useState } from "react";
import type { Capsule, TraceEvent } from "../../types";
import CapsuleCard from "../capsule/CapsuleCard";

const EVENT_META: Record<string, { label: string; color: string; icon: string }> = {
  trace_start:          { label: "Started",          color: "text-blue-600 border-blue-200 bg-blue-50",          icon: "▶" },
  memory_loaded:        { label: "Memory loaded",    color: "text-purple-600 border-purple-200 bg-purple-50",    icon: "🧠" },
  skills_loaded:        { label: "Skills loaded",    color: "text-violet-600 border-violet-200 bg-violet-50",    icon: "⚡" },
  skill_tool_call:      { label: "Fetching skill",   color: "text-teal-600 border-teal-200 bg-teal-50",          icon: "↓" },
  skill_tool_result:    { label: "Skill fetched",    color: "text-emerald-600 border-emerald-200 bg-emerald-50", icon: "✓" },
  rag_start:            { label: "RAG search",       color: "text-amber-600 border-amber-200 bg-amber-50",       icon: "🔍" },
  rag_result:           { label: "RAG result",       color: "text-emerald-600 border-emerald-200 bg-emerald-50", icon: "📄" },
  llm_start:            { label: "LLM call",         color: "text-orange-600 border-orange-200 bg-orange-50",    icon: "⚡" },
  llm_end:              { label: "LLM done",         color: "text-green-600 border-green-200 bg-green-50",       icon: "✓" },
  capsule_creating:     { label: "Creating capsule", color: "text-sky-600 border-sky-200 bg-sky-50",             icon: "📦" },
  capsule_created:      { label: "Capsule saved",    color: "text-emerald-600 border-emerald-200 bg-emerald-50", icon: "📦" },
  capsule_error:        { label: "Capsule failed",   color: "text-red-600 border-red-200 bg-red-50",             icon: "📦" },
  manager_routing:      { label: "Routing decision", color: "text-indigo-600 border-indigo-200 bg-indigo-50",    icon: "🔀" },
  manager_delegating:   { label: "Delegating",       color: "text-indigo-600 border-indigo-200 bg-indigo-50",    icon: "📤" },
  manager_agent_call:   { label: "Agent called",     color: "text-sky-600 border-sky-200 bg-sky-50",             icon: "→" },
  manager_agent_result: { label: "Agent responded",  color: "text-teal-600 border-teal-200 bg-teal-50",          icon: "←" },
  manager_synthesis:    { label: "Synthesizing",     color: "text-violet-600 border-violet-200 bg-violet-50",    icon: "⚙" },
  error:                { label: "Error",            color: "text-red-600 border-red-200 bg-red-50",             icon: "✕" },
};

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      className={`w-3 h-3 transition-transform duration-150 ${open ? "rotate-180" : ""}`}
      viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"
    >
      <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

type RagChunk = { rag_id: string; chunk_id: string; name: string; score: number; data: string; source: string | null };
type MemoryTurn = { role: string; content: string };

export default function TraceEventCard({ event, capsule }: { event: TraceEvent; capsule?: Capsule }) {
  const [expanded, setExpanded] = useState(false);
  const meta = EVENT_META[event.type] ?? { label: event.type, color: "text-slate-600 border-border bg-surface", icon: "•" };
  const data = event.data as Record<string, unknown>;

  const chunks = Array.isArray(data.chunks) ? (data.chunks as RagChunk[]) : [];
  const history = Array.isArray(data.history) ? (data.history as MemoryTurn[]) : [];
  const skills = Array.isArray(data.skills) ? (data.skills as { id: string; name: string }[]) : [];
  const hasExpander = (event.type === "rag_result" && chunks.length > 0)
    || (event.type === "memory_loaded" && history.length > 0);

  return (
    <div className={`text-xs rounded-lg border ${meta.color} overflow-hidden`}>
      {/* Header row */}
      <div
        className={`flex items-center gap-1.5 font-medium px-3 py-2 ${hasExpander ? "cursor-pointer select-none" : ""}`}
        onClick={hasExpander ? () => setExpanded((v) => !v) : undefined}
      >
        <span>{meta.icon}</span>
        <span>{meta.label}</span>

        {/* inline summary chips */}
        {event.type === "rag_start" && data.query && (
          <span className="ml-1 font-normal opacity-70 truncate max-w-[160px]">"{String(data.query)}"</span>
        )}
        {event.type === "rag_result" && (
          <span className="ml-1 font-normal opacity-70">{chunks.length} chunk{chunks.length !== 1 ? "s" : ""}</span>
        )}
        {event.type === "memory_loaded" && (
          <span className="ml-1 font-normal opacity-70">{String(data.messages_loaded ?? 0)} msg{Number(data.messages_loaded) !== 1 ? "s" : ""}</span>
        )}
        {(event.type === "llm_start" || event.type === "llm_end") && data.model && (
          <span className="ml-1 font-mono font-normal opacity-70 truncate">{String(data.model)}</span>
        )}
        {event.type === "trace_start" && data.model && (
          <span className="ml-1 font-mono font-normal opacity-70 truncate">{String(data.model)}</span>
        )}

        <span className="ml-auto font-normal opacity-60 text-[10px] flex-shrink-0">{new Date(event.ts).toLocaleTimeString()}</span>
        {hasExpander && <ChevronIcon open={expanded} />}
      </div>

      {/* rag_start details */}
      {event.type === "rag_start" && (
        <div className="px-3 pb-2 space-y-1 border-t border-amber-200/60">
          <p className="mt-1.5 font-mono opacity-80 break-words">{String(data.query)}</p>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {data.retrieval_type && (
              <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">{String(data.retrieval_type)}</span>
            )}
            {data.top_k && (
              <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">top {String(data.top_k)}</span>
            )}
          </div>
        </div>
      )}

      {/* rag_result expandable chunks */}
      {event.type === "rag_result" && expanded && chunks.length > 0 && (
        <div className="border-t border-emerald-200/60 divide-y divide-emerald-200/40">
          {chunks.map((c, i) => (
            <div key={c.chunk_id ?? i} className="px-3 py-2 space-y-0.5">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium truncate">{c.name || c.chunk_id}</span>
                <span className="flex-shrink-0 font-mono bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded">
                  {(c.score * 100).toFixed(1)}%
                </span>
              </div>
              {c.source && <p className="opacity-50 truncate">source: {c.source}</p>}
              <p className="opacity-70 leading-relaxed line-clamp-3 whitespace-pre-wrap">{c.data}</p>
            </div>
          ))}
        </div>
      )}

      {/* memory_loaded expandable history */}
      {event.type === "memory_loaded" && expanded && history.length > 0 && (
        <div className="border-t border-purple-200/60 divide-y divide-purple-200/40">
          {history.map((turn, i) => (
            <div key={i} className="px-3 py-1.5 flex gap-2">
              <span className={`flex-shrink-0 font-medium w-14 ${turn.role === "user" ? "text-purple-700" : "opacity-50"}`}>
                {turn.role}
              </span>
              <p className="opacity-70 truncate">{turn.content}</p>
            </div>
          ))}
        </div>
      )}

      {/* skills_loaded pills */}
      {event.type === "skills_loaded" && skills.length > 0 && (
        <div className="px-3 pb-2 flex flex-wrap gap-1 border-t border-violet-200/60 pt-1.5">
          {skills.map((s) => (
            <span key={s.id} className="px-1.5 py-0.5 rounded bg-violet-100 text-violet-700 font-medium">{s.name}</span>
          ))}
        </div>
      )}

      {/* skill tool call / result */}
      {event.type === "skill_tool_call" && data.skill_name && (
        <div className="px-3 pb-2 border-t border-teal-200/60 pt-1.5">
          <p className="font-mono opacity-80">→ {String(data.skill_name)}</p>
        </div>
      )}
      {event.type === "skill_tool_result" && data.skill_name && (
        <div className="px-3 pb-2 border-t border-emerald-200/60 pt-1.5">
          <span className="font-mono opacity-80">{String(data.skill_name)}</span>
          {data.content_length !== undefined && (
            <span className="opacity-40 ml-1.5">({String(data.content_length)} chars)</span>
          )}
        </div>
      )}

      {/* capsule events */}
      {event.type === "capsule_creating" && data.name && (
        <div className="px-3 pb-2 border-t border-sky-200/60 pt-1.5 flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full border-2 border-sky-400 border-t-transparent animate-spin flex-shrink-0" />
          <span className="opacity-80 truncate">{String(data.name)}</span>
          {data.format_type && (
            <span className="ml-auto text-[10px] font-medium uppercase tracking-wider opacity-50 flex-shrink-0">
              {String(data.format_type)}
            </span>
          )}
        </div>
      )}
      {event.type === "capsule_created" && (
        <div className="px-3 pb-3 border-t border-emerald-200/60 pt-2">
          {capsule ? (
            <CapsuleCard capsule={capsule} />
          ) : (
            <div className="flex items-center gap-2 text-xs opacity-70">
              <span className="font-mono truncate">{String(data.name ?? "Capsule")}</span>
              {data.format_type && (
                <span className="text-[10px] font-medium uppercase tracking-wider opacity-50">{String(data.format_type)}</span>
              )}
              {data.has_file && <span className="ml-auto text-emerald-600">+ file</span>}
            </div>
          )}
        </div>
      )}
      {event.type === "capsule_error" && data.detail && (
        <div className="px-3 pb-2 border-t border-red-200/60 pt-1.5">
          <p className="font-mono opacity-80 break-words">{String(data.detail)}</p>
        </div>
      )}

      {/* error */}
      {event.type === "error" && data.detail && (
        <div className="px-3 pb-2 border-t border-red-200/60 pt-1.5">
          <p className="font-mono opacity-80 break-words">{String(data.detail)}</p>
        </div>
      )}

      {/* manager events */}
      {data.agent_name && (
        <div className="px-3 pb-2 border-t border-current/10 pt-1.5">
          <p className="opacity-80">→ {String(data.agent_name)}</p>
        </div>
      )}
      {data.decision && (
        <div className="px-3 pb-2 border-t border-current/10 pt-1.5">
          <p className="opacity-80">{String(data.decision)}</p>
        </div>
      )}
    </div>
  );
}
