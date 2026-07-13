import { useCopy } from "../../hooks/useCopy";

export function tryParseJson(str: string): object | null {
  const t = str.trim();
  if (!t.startsWith("{") && !t.startsWith("[")) return null;
  try { return JSON.parse(t); } catch { return null; }
}

const CheckIcon = () => (
  <svg className="w-2.5 h-2.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5">
    <path d="M2 8l4 4 8-8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const CopyIcon = () => (
  <svg className="w-2.5 h-2.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="5" y="5" width="9" height="9" rx="1.5" />
    <path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5" strokeLinecap="round" />
  </svg>
);

export default function JsonBlock({ raw }: { raw: string }) {
  const { copied, copy } = useCopy();
  const formatted = JSON.stringify(JSON.parse(raw), null, 2);
  return (
    <div className="max-w-[85%] rounded-2xl rounded-bl-sm overflow-hidden border border-zinc-600/50 bg-zinc-800 text-left animate-fade-in">
      <div className="flex items-center justify-between px-3.5 py-2 border-b border-zinc-600/50 bg-zinc-700/70">
        <div className="flex items-center gap-1.5">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3 h-3 text-accent-light">
            <path d="M5 2H3.5A1.5 1.5 0 002 3.5v2M5 14H3.5A1.5 1.5 0 012 12.5v-2M11 2h1.5A1.5 1.5 0 0114 3.5v2M11 14h1.5a1.5 1.5 0 001.5-1.5v-2" strokeLinecap="round"/>
          </svg>
          <span className="text-[10px] font-bold tracking-widest text-accent-light uppercase">JSON</span>
        </div>
        <button
          onClick={() => copy(formatted)}
          className="flex items-center gap-1 text-[10px] font-semibold tracking-wide text-slate-400 hover:text-slate-200 transition-colors"
        >
          {copied ? <><CheckIcon /> COPIED</> : <><CopyIcon /> COPY</>}
        </button>
      </div>
      <pre className="overflow-auto text-[11px] leading-relaxed text-slate-200 font-mono p-3.5 max-h-80 whitespace-pre-wrap break-words">
        {formatted}
      </pre>
    </div>
  );
}
