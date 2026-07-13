import { useRef, useState } from "react";
import { api } from "../../api";
import Dialog from "../Dialog";
import Input from "../Input";

interface Props {
  ragId: string;
  onDone: () => void;
  onClose: () => void;
}

export default function AddFileModal({ ragId, onDone, onClose }: Props) {
  const [file, setFile]           = useState<File | null>(null);
  const [name, setName]           = useState("");
  const [source, setSource]       = useState("");
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [result, setResult]       = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) { setFile(f); if (!name) setName(f.name); }
  }

  async function handleSubmit() {
    if (!file) { setError("Please select a file."); return; }
    setSaving(true); setError(null);
    const fd = new FormData();
    fd.append("file", file);
    if (name.trim()) fd.append("name", name.trim());
    if (source.trim()) fd.append("source", source.trim());
    fd.append("chunk_size", String(chunkSize));
    fd.append("chunk_overlap", String(chunkOverlap));
    try {
      const res = await api.insertFile(ragId, fd);
      setResult(res.chunks_created);
      onDone();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Upload failed"); }
    finally { setSaving(false); }
  }

  const footer = (
    <>
      <button onClick={onClose} className="px-4 py-2 border border-border rounded-lg text-sm text-muted hover:bg-bg transition-colors">
        {result !== null ? "Close" : "Cancel"}
      </button>
      <button onClick={handleSubmit} disabled={saving || !file} className="flex-1 py-2 bg-accent hover:bg-accent-muted disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors">
        {saving ? "Uploading & embedding…" : "Upload to RAG"}
      </button>
    </>
  );

  return (
    <Dialog title="Add File" size="md" onClose={onClose} footer={footer}>
      <div className="space-y-4">
        <div
          onDrop={handleDrop} onDragOver={e => e.preventDefault()}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
            file ? "border-accent-light bg-accent-faint" : "border-border hover:border-accent-light/50 hover:bg-bg"
          }`}
        >
          <input ref={inputRef} type="file" accept=".txt,.md,.csv,.json,.xml,.html,.htm"
            onChange={e => { const f = e.target.files?.[0]; if (f) { setFile(f); if (!name) setName(f.name); } }}
            className="hidden" />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <span className="text-2xl">📄</span>
              <div className="text-left">
                <p className="text-slate-800 text-sm font-medium">{file.name}</p>
                <p className="text-muted text-xs">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
              <button onClick={e => { e.stopPropagation(); setFile(null); setName(""); }}
                className="ml-auto text-muted hover:text-red-500 transition-colors text-sm">✕</button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <span className="text-3xl">📁</span>
              <p className="text-slate-700 text-sm font-medium">Drop a file here or click to browse</p>
              <p className="text-muted text-xs">.txt · .md · .csv · .json · .xml · .html</p>
            </div>
          )}
        </div>
        <div>
          <label className="type-label block mb-1.5">Document Name <span className="text-muted normal-case font-normal">(defaults to filename)</span></label>
          <Input value={name} onChange={e => setName(e.target.value)} placeholder="Override filename…" />
        </div>
        <div>
          <label className="type-label block mb-1.5">Source <span className="text-muted normal-case font-normal">(optional)</span></label>
          <Input value={source} onChange={e => setSource(e.target.value)} placeholder="URL, system name…" />
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
            ✓ Uploaded — {result} chunk{result !== 1 ? "s" : ""} created
          </div>
        )}
        {error && <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-600 text-xs">{error}</div>}
      </div>
    </Dialog>
  );
}
