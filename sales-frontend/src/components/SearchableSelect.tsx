import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export interface SearchableSelectOption {
  value: string;
  label: string;
  description?: string;
}

interface SearchableSelectProps {
  options: SearchableSelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyLabel?: string;
  emptyMessage?: string;
  size?: "sm" | "md";
  className?: string;
}

export default function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  emptyLabel = "— None —",
  emptyMessage = "No results",
  size = "md",
  className = "",
}: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [dropPos, setDropPos] = useState({ top: 0, left: 0, width: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);

  const selected = options.find((o) => o.value === value);
  const filtered = query.trim()
    ? options.filter(
        (o) =>
          o.label.toLowerCase().includes(query.toLowerCase()) ||
          o.description?.toLowerCase().includes(query.toLowerCase())
      )
    : options;

  function toggle() {
    if (open) { close(); return; }
    if (triggerRef.current) {
      const r = triggerRef.current.getBoundingClientRect();
      setDropPos({ top: r.bottom + 4, left: r.left, width: r.width });
    }
    setOpen(true);
  }

  function close() {
    setOpen(false);
    setQuery("");
  }

  function pick(val: string) {
    onChange(val);
    close();
  }

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") { setOpen(false); setQuery(""); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const triggerBase = "w-full bg-surface border border-border rounded-lg text-left flex items-center justify-between gap-2 focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors";
  const triggerSizing = size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3 py-2.5 text-sm";

  return (
    <div className={className}>
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        className={`${triggerBase} ${triggerSizing} ${open ? "border-accent-light ring-2 ring-accent-light/20" : "hover:border-slate-300"}`}
      >
        <span className={`truncate flex-1 ${selected ? "text-slate-800" : "text-muted"}`}>
          {selected?.label ?? placeholder}
        </span>
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className={`w-3.5 h-3.5 text-muted flex-shrink-0 transition-transform ${open ? "rotate-180" : ""}`}>
          <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && createPortal(
        <>
          <div className="fixed inset-0 z-[199]" onClick={close} />
          <div
            style={{ top: dropPos.top, left: dropPos.left, width: dropPos.width }}
            className="fixed z-[200] bg-surface border border-border rounded-xl shadow-lg overflow-hidden"
          >
            <div className="p-2 border-b border-border">
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full bg-bg border border-border rounded-lg px-2.5 py-1.5 text-xs text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light transition-colors"
              />
            </div>
            <div className="max-h-52 overflow-y-auto scrollbar-thin">
              {value && emptyLabel && (
                <button type="button" onClick={() => pick("")} className="w-full text-left px-3 py-2 text-xs text-muted hover:bg-bg transition-colors border-b border-border">
                  ✕ {emptyLabel}
                </button>
              )}
              {filtered.length === 0 ? (
                <p className="text-xs text-muted text-center px-3 py-4">{emptyMessage}</p>
              ) : (
                filtered.map((o) => (
                  <button
                    key={o.value}
                    type="button"
                    onClick={() => pick(o.value)}
                    className={`w-full text-left px-3 py-2 text-xs transition-colors hover:bg-bg ${o.value === value ? "bg-accent-faint text-accent" : "text-slate-700"}`}
                  >
                    <p className={`font-medium truncate ${o.value === value ? "text-accent" : ""}`}>{o.label}</p>
                    {o.description && <p className="text-muted truncate mt-0.5">{o.description}</p>}
                  </button>
                ))
              )}
            </div>
          </div>
        </>,
        document.body
      )}
    </div>
  );
}
