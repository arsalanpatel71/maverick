import { useState } from "react";
import { api } from "../../api";
import Dialog from "../Dialog";
import Input from "../Input";

interface Props {
  ragId: string;
  onDone: () => void;
  onClose: () => void;
}

export default function AddTextModal({ ragId, onDone, onClose }: Props) {
  const [name, setName]       = useState("");
  const [data, setData]       = useState("");
  const [source, setSource]   = useState("");
  const [chunkSize, setChunkSize]     = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const [result, setResult]   = useState<number | null>(null);

  async function handleSubmit() {
    if (!name.trim() || !data.trim()) { setError("Name and content are required."); return; }
    setSaving(true); setError(null);
    try {
      const res = await api.insertText(ragId, {
        name: name.trim(), data: data.trim(),
        source: source.trim() || null, chunk_size: chunkSize, chunk_overlap: chunkOverlap,
      });
      setResult(res.chunks_created);
      onDone();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Insert failed"); }
    finally { setSaving(false); }
  }

  const footer = (
    <>
      <button onClick={onClose} className="px-4 py-2 border border-border rounded-lg text-sm text-muted hover:bg-bg transition-colors">
        {result !== null ? "Close" : "Cancel"}
      </button>
      <button onClick={handleSubmit} disabled={saving} className="flex-1 py-2 bg-accent hover:bg-accent-muted disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors">
        {saving ? "Embedding…" : "Add to RAG"}
      </button>
    </>
  );

  return (
    <Dialog title="Add Text" size="md" onClose={onClose} footer={footer}>
      <div className="space-y-4">
        <div>
          <label className="type-label block mb-1.5">Document Name *</label>
          <Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Getting Started Guide" />
        </div>
        <div>
          <label className="type-label block mb-1.5">Source <span className="text-muted normal-case font-normal">(optional)</span></label>
          <Input value={source} onChange={e => setSource(e.target.value)} placeholder="URL, document title…" />
        </div>
        <div>
          <label className="type-label block mb-1.5">Content *</label>
          <textarea value={data} onChange={e => setData(e.target.value)} rows={8}
            placeholder="Paste or type the text content…"
            className="w-full bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors resize-none font-mono leading-relaxed" />
          <p className="type-caption mt-1">{data.length.toLocaleString()} characters</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="type-label block mb-1.5">Chunk Size</label>
            <Input type="number" min={100} max={8000} value={chunkSize} onChange={e => setChunkSize(parseInt(e.target.value) || 1000)} />
          </div>
          <div>
            <label className="type-label block mb-1.5">Chunk Overlap</label>
            <Input type="number" min={0} max={2000} value={chunkOverlap} onChange={e => setChunkOverlap(parseInt(e.target.value) || 200)} />
          </div>
        </div>
        {result !== null && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3 text-emerald-700 text-xs">
            ✓ Inserted — {result} chunk{result !== 1 ? "s" : ""} created
          </div>
        )}
        {error && <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-600 text-xs">{error}</div>}
      </div>
    </Dialog>
  );
}
