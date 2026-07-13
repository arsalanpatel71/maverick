import type { PageMeta } from "../types";

interface Props {
  meta: PageMeta;
  onChange: (page: number) => void;
}

export default function Pagination({ meta, onChange }: Props) {
  if (meta.pages <= 1) return null;

  const { page, pages } = meta;

  const pages_list: (number | "…")[] = [];
  if (pages <= 7) {
    for (let i = 1; i <= pages; i++) pages_list.push(i);
  } else {
    pages_list.push(1);
    if (page > 3) pages_list.push("…");
    for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) pages_list.push(i);
    if (page < pages - 2) pages_list.push("…");
    pages_list.push(pages);
  }

  const btn = "min-w-[2rem] h-8 px-2 rounded-lg text-xs font-medium transition-colors";

  return (
    <div className="flex items-center justify-center gap-1 py-4">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page === 1}
        className={`${btn} text-muted hover:bg-bg border border-border disabled:opacity-30`}
      >
        ‹
      </button>

      {pages_list.map((p, i) =>
        p === "…" ? (
          <span key={`dots-${i}`} className="px-1 text-xs text-muted">…</span>
        ) : (
          <button
            key={p}
            onClick={() => onChange(p)}
            className={`${btn} border ${p === page ? "bg-accent text-white border-accent" : "border-border text-slate-700 hover:bg-bg"}`}
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onChange(page + 1)}
        disabled={page === pages}
        className={`${btn} text-muted hover:bg-bg border border-border disabled:opacity-30`}
      >
        ›
      </button>
    </div>
  );
}
