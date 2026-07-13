import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "../../api";
import type { Capsule } from "../../types";

const FORMAT_ICONS: Record<string, string> = {
  text: "📄", code: "💻", json: "{ }", markdown: "✍️", data: "📊",
  image: "🖼️", csv: "📋", xlsx: "📊", pdf: "📕", docx: "📝", pptx: "📑",
};

const FORMAT_COLORS: Record<string, string> = {
  text:     "border-slate-200 bg-slate-50 text-slate-700",
  code:     "border-violet-200 bg-violet-50 text-violet-700",
  json:     "border-sky-200 bg-sky-50 text-sky-700",
  markdown: "border-teal-200 bg-teal-50 text-teal-700",
  data:     "border-amber-200 bg-amber-50 text-amber-700",
  image:    "border-pink-200 bg-pink-50 text-pink-700",
  csv:      "border-green-200 bg-green-50 text-green-700",
  xlsx:     "border-emerald-200 bg-emerald-50 text-emerald-700",
  pdf:      "border-red-200 bg-red-50 text-red-700",
  docx:     "border-blue-200 bg-blue-50 text-blue-700",
  pptx:     "border-orange-200 bg-orange-50 text-orange-700",
};

const FILE_FORMATS = new Set(["csv", "xlsx", "pdf", "docx", "pptx"]);

function JsonViewer({ data }: { data: string }) {
  const [collapsed, setCollapsed] = useState(true);
  let parsed: unknown;
  let isValid = true;
  try {
    parsed = JSON.parse(data);
  } catch {
    isValid = false;
  }

  if (!isValid) {
    return <pre className="text-xs font-mono whitespace-pre-wrap text-slate-600 max-h-48 overflow-y-auto">{data}</pre>;
  }

  const full = JSON.stringify(parsed, null, 2);
  const preview = full.slice(0, 300) + (full.length > 300 ? "\n…" : "");

  return (
    <div>
      <pre className="text-xs font-mono whitespace-pre-wrap text-slate-600 max-h-48 overflow-y-auto">
        {collapsed && full.length > 300 ? preview : full}
      </pre>
      {full.length > 300 && (
        <button
          onClick={() => setCollapsed((v) => !v)}
          className="mt-1 text-xs text-sky-600 hover:underline"
        >
          {collapsed ? "Show more" : "Show less"}
        </button>
      )}
    </div>
  );
}

function FileDownload({ capsule, onRefreshed }: { capsule: Capsule; onRefreshed: (url: string) => void }) {
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileUrl = capsule.metadata.file_url;
  const fileName = capsule.metadata.file_name ?? `${capsule.name}`;

  async function handleRefresh() {
    setRefreshing(true);
    setError(null);
    try {
      const { file_url } = await api.refreshCapsuleUrl(capsule.capsule_id);
      onRefreshed(file_url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to refresh");
    } finally {
      setRefreshing(false);
    }
  }

  if (!fileUrl) {
    return (
      <div className="text-xs text-amber-600 flex items-center gap-1.5">
        <span>⚠️</span>
        <span>File not yet rendered.</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <a
        href={fileUrl}
        download={fileName}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
      >
        ⬇ {fileName}
      </a>
      <button
        onClick={handleRefresh}
        disabled={refreshing}
        title="Regenerate download link (URLs expire after 1 hour)"
        className="text-xs text-slate-400 hover:text-slate-600 disabled:opacity-50 transition-colors"
      >
        {refreshing ? "Refreshing…" : "↻ Refresh link"}
      </button>
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
}

interface CapsuleCardProps {
  capsule: Capsule;
  onDeleted?: () => void;
}

function CopyId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  function copy(e: React.MouseEvent) {
    e.stopPropagation();
    navigator.clipboard.writeText(id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }
  return (
    <button
      onClick={copy}
      title="Copy capsule ID"
      className="font-mono text-[10px] opacity-40 hover:opacity-80 transition-opacity select-all flex-shrink-0 leading-none"
    >
      {copied ? "copied!" : id.slice(0, 8) + "…"}
    </button>
  );
}

export default function CapsuleCard({ capsule, onDeleted }: CapsuleCardProps) {
  const [fileUrl, setFileUrl] = useState(capsule.metadata.file_url);
  const [deleting, setDeleting] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const fmt = capsule.format_type;
  const colorCls = FORMAT_COLORS[fmt] ?? FORMAT_COLORS.text;
  const icon = FORMAT_ICONS[fmt] ?? "📄";
  const isFile = FILE_FORMATS.has(fmt);
  const hasContent = capsule.data && capsule.data.length > 0;
  const canExpand = !isFile && hasContent;

  async function handleDelete() {
    setDeleting(true);
    try {
      await api.deleteCapsule(capsule.capsule_id);
      onDeleted?.();
    } catch {
      setDeleting(false);
    }
  }

  return (
    <div className={`rounded-xl border text-xs overflow-hidden ${colorCls}`}>
      {/* Header */}
      <div
        className={`flex items-center gap-2 px-3 py-2 ${canExpand ? "cursor-pointer select-none" : ""}`}
        onClick={canExpand ? () => setExpanded((v) => !v) : undefined}
      >
        <span className="text-sm leading-none flex-shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{capsule.name}</p>
          <p className="opacity-60 truncate text-[10px] mt-0.5">{capsule.description}</p>
        </div>
        <span className="flex-shrink-0 text-[10px] font-medium uppercase tracking-wider opacity-60">
          {fmt}
        </span>
        <CopyId id={capsule.capsule_id} />
        {canExpand && (
          <svg
            className={`w-3 h-3 flex-shrink-0 transition-transform ${expanded ? "rotate-180" : ""}`}
            viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"
          >
            <path d="M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
        {onDeleted && (
          <button
            onClick={(e) => { e.stopPropagation(); handleDelete(); }}
            disabled={deleting}
            className="flex-shrink-0 opacity-30 hover:opacity-70 transition-opacity ml-1 disabled:opacity-20"
            title="Delete capsule"
          >
            ✕
          </button>
        )}
      </div>

      {/* Content */}
      {isFile ? (
        <div className="px-3 pb-3 pt-0 border-t border-current/10">
          <FileDownload
            capsule={{ ...capsule, metadata: { ...capsule.metadata, file_url: fileUrl } }}
            onRefreshed={setFileUrl}
          />
        </div>
      ) : expanded && hasContent ? (
        <div className="px-3 pb-3 border-t border-current/10 pt-2 max-h-80 overflow-y-auto">
          {fmt === "markdown" || fmt === "text" ? (
            fmt === "markdown" ? (
              <div className="prose prose-xs prose-slate max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{capsule.data!}</ReactMarkdown>
              </div>
            ) : (
              <p className="whitespace-pre-wrap text-xs leading-relaxed">{capsule.data}</p>
            )
          ) : fmt === "code" ? (
            <pre className={`text-xs font-mono whitespace-pre-wrap leading-relaxed overflow-x-auto`}>
              {capsule.data}
            </pre>
          ) : fmt === "image" ? (
            <img src={capsule.data!} alt={capsule.name} className="max-w-full rounded" />
          ) : (
            <JsonViewer data={capsule.data!} />
          )}
        </div>
      ) : null}
    </div>
  );
}
