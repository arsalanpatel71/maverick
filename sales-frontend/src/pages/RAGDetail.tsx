import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

const EMBEDDING_MODELS: Record<string, { id: string; dims: number }[]> = {
  openai: [
    { id: "text-embedding-3-small", dims: 1536 },
    { id: "text-embedding-3-large", dims: 3072 },
    { id: "text-embedding-ada-002", dims: 1536 },
  ],
  gemini: [
    { id: "gemini-embedding-001", dims: 3072 },
    { id: "gemini-embedding-2", dims: 3072 },
    { id: "gemini-embedding-2-preview", dims: 3072 },
  ],
};

interface FormState {
  name: string;
  description: string;
  embedding_provider: string;
  embedding_model: string;
}

export default function RAGDetail() {
  const navigate = useNavigate();

  const [form, setForm] = useState<FormState>({
    name: "",
    description: "",
    embedding_provider: "gemini",
    embedding_model: "gemini-embedding-001",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function handleProviderChange(provider: string) {
    const models = EMBEDDING_MODELS[provider] ?? [];
    setForm((f) => ({ ...f, embedding_provider: provider, embedding_model: models[0]?.id ?? "" }));
  }

  async function handleCreate() {
    if (!form.name.trim()) { setError("Name is required."); return; }
    setSaving(true);
    setError(null);
    try {
      await api.createRag({
        name: form.name.trim(),
        description: form.description.trim() || null,
        vector_store: "qdrant",
        embedding_provider: form.embedding_provider,
        embedding_model: form.embedding_model,
      });
      navigate("/rags");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setSaving(false);
    }
  }

  const currentModels = EMBEDDING_MODELS[form.embedding_provider] ?? [];
  const selectedModel = currentModels.find((m) => m.id === form.embedding_model);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="border-b border-border px-8 py-4 flex items-center gap-3 flex-shrink-0 bg-surface">
        <button onClick={() => navigate("/rags")} className="text-muted hover:text-slate-700 transition-colors text-sm">
          ← RAGs
        </button>
        <span className="text-border">|</span>
        <span className="text-slate-900 text-sm font-medium">New Knowledge Base</span>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin px-8 py-6">
        <div className="max-w-xl space-y-5">

          <div>
            <label className="type-label block mb-1.5">Name <span className="text-red-500 normal-case font-normal">*</span></label>
            <input
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="e.g. Product Docs, Onboarding Guide…"
              className="w-full bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors"
            />
          </div>

          <div>
            <label className="type-label block mb-1.5">Description <span className="text-muted normal-case font-normal text-[10px] ml-1">optional</span></label>
            <textarea
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              rows={3}
              placeholder="What does this knowledge base contain?"
              className="w-full bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors resize-none"
            />
          </div>

          <div>
            <label className="type-label block mb-1.5">Embedding</label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="type-label-sm block mb-1">Provider</label>
                <select
                  value={form.embedding_provider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors"
                >
                  <option value="gemini">Gemini</option>
                  <option value="openai">OpenAI</option>
                </select>
              </div>
              <div>
                <label className="type-label-sm block mb-1">Model</label>
                <select
                  value={form.embedding_model}
                  onChange={(e) => set("embedding_model", e.target.value)}
                  className="w-full bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors font-mono"
                >
                  {currentModels.map((m) => <option key={m.id} value={m.id}>{m.id}</option>)}
                </select>
              </div>
            </div>
            {selectedModel && (
              <p className="type-caption mt-1.5">
                Dimensions: <span className="font-mono text-slate-500">{selectedModel.dims}</span>
                {" · "}Store: <span className="font-mono text-slate-500">qdrant</span>
              </p>
            )}
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-600">
            After creating this RAG, upload documents via the knowledge base page to populate it.
          </div>

          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={handleCreate}
              disabled={saving || !form.name.trim()}
              className="px-5 py-2 bg-accent hover:bg-accent-muted disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
            >
              {saving ? "Creating…" : "Create RAG"}
            </button>
            <button
              onClick={() => navigate("/rags")}
              className="px-4 py-2 bg-surface border border-border hover:bg-bg text-slate-600 rounded-lg text-sm transition-colors"
            >
              Cancel
            </button>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-600 text-xs">{error}</div>
          )}

        </div>
      </div>
    </div>
  );
}
