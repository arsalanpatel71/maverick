import { useEffect, useState } from "react";
import { api } from "../api";
import type { PageMeta, Skill, SkillCatalogEntry } from "../types";
import Spinner from "../components/Spinner";
import Input from "../components/Input";
import Pagination from "../components/Pagination";
import { useDebounce } from "../hooks/useDebounce";
import { skillColor, skillInitials } from "../utils/skillColor";
import { inputCls } from "../components/agent/types";

function SkillAvatar({ name }: { name: string }) {
  return (
    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0 ${skillColor(name)}`}>
      {skillInitials(name)}
    </div>
  );
}

// ── Catalog card ─────────────────────────────────────────────────────────────

function CatalogCard({
  entry,
  onImported,
}: {
  entry: SkillCatalogEntry;
  onImported: (skill: Skill) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [imported, setImported] = useState(entry.imported);
  const [error, setError] = useState<string | null>(null);

  async function handleAdd() {
    setLoading(true);
    setError(null);
    try {
      const skill = await api.importSkillFromGithub(entry.github_url);
      setImported(true);
      onImported(skill);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to import");
      setLoading(false);
    }
  }

  return (
    <div className={`bg-surface border rounded-xl p-4 flex flex-col gap-3 transition-colors ${imported ? "border-accent-light/60" : "border-border hover:border-accent-light/40"}`}>
      <div className="flex items-start gap-3">
        <SkillAvatar name={entry.name} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-800 truncate">{entry.name}</h3>
            {imported && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-accent-faint text-accent border border-accent-light/50 flex-shrink-0">added</span>
            )}
          </div>
          <p className="text-xs text-muted mt-1 leading-relaxed line-clamp-3">{entry.description}</p>
        </div>
      </div>

      <a
        href={entry.github_url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[11px] text-accent hover:underline truncate"
      >
        View on GitHub ↗
      </a>

      {error && <p className="text-[11px] text-red-500">{error}</p>}

      {!imported && (
        <button
          onClick={handleAdd}
          disabled={loading}
          className="self-start px-3 py-1.5 bg-accent hover:bg-accent-muted disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-medium rounded-lg transition-colors"
        >
          {loading ? "Adding…" : "Add skill"}
        </button>
      )}
    </div>
  );
}

// ── My skill card ─────────────────────────────────────────────────────────────

function SkillCard({ skill, onDelete }: { skill: Skill; onDelete: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (!confirm(`Delete skill "${skill.name}"?`)) return;
    setDeleting(true);
    try {
      await api.deleteSkill(skill.id);
      onDelete(skill.id);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to delete skill");
      setDeleting(false);
    }
  }

  const body = skill.content.replace(/^---[\s\S]*?---\s*/m, "").trim();

  const sourceBadge =
    skill.source === "github"
      ? <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500">github</span>
      : <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600">custom</span>;

  return (
    <div className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-3 hover:border-accent-light/40 transition-colors">
      <div className="flex items-start gap-3">
        <SkillAvatar name={skill.name} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-slate-800 truncate">{skill.name}</p>
            {sourceBadge}
          </div>
          <p className="text-xs text-muted mt-1 leading-relaxed line-clamp-2">{skill.description}</p>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="flex-shrink-0 text-muted hover:text-red-500 disabled:opacity-40 transition-colors"
          title="Delete"
        >
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
            <path d="M2 4h12M5 4V2h6v2M6 7v5M10 7v5M3 4l1 10h8l1-10" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {skill.github_url && (
        <a href={skill.github_url} target="_blank" rel="noopener noreferrer" className="text-[11px] text-accent hover:underline truncate">
          {skill.github_url}
        </a>
      )}

      <button
        onClick={() => setExpanded((p) => !p)}
        className="text-[11px] text-muted hover:text-slate-600 transition-colors text-left"
      >
        {expanded ? "▲ Hide content" : "▼ View content"}
      </button>

      {expanded && (
        <pre className="text-[11px] bg-bg border border-border rounded-lg p-3 overflow-x-auto whitespace-pre-wrap text-slate-700 leading-relaxed max-h-56 overflow-y-auto scrollbar-thin">
          {body}
        </pre>
      )}
    </div>
  );
}

// ── Import custom GitHub modal ────────────────────────────────────────────────

function ImportGithubModal({ onImported, onClose }: { onImported: (skill: Skill) => void; onClose: () => void }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleImport() {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const skill = await api.importSkillFromGithub(url.trim());
      onImported(skill);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to import skill");
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-surface border border-border rounded-2xl shadow-xl w-full max-w-md mx-4 p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Import from GitHub URL</h2>
          <button onClick={onClose} className="text-muted hover:text-slate-600 transition-colors">✕</button>
        </div>
        <div className="space-y-1.5">
          <label className="type-label">GitHub URL to SKILL.md</label>
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repo/blob/main/SKILL.md"
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && handleImport()}
          />
          <p className="text-[11px] text-muted">
            Must contain a <code className="font-mono">SKILL.md</code> with <code className="font-mono">name</code> and <code className="font-mono">description</code> in YAML frontmatter.
          </p>
        </div>
        {error && <p className="text-xs text-red-500">{error}</p>}
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-3 py-1.5 text-xs text-muted hover:text-slate-600 transition-colors">Cancel</button>
          <button
            onClick={handleImport}
            disabled={loading || !url.trim()}
            className="px-4 py-1.5 bg-accent hover:bg-accent-muted disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-xs font-medium transition-colors"
          >
            {loading ? "Importing…" : "Import"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Create custom skill modal ─────────────────────────────────────────────────

function CreateCustomModal({ onCreated, onClose }: { onCreated: (skill: Skill) => void; onClose: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate() {
    if (!name.trim() || !description.trim() || !content.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const skill = await api.createSkill({ name: name.trim(), description: description.trim(), content: content.trim() });
      onCreated(skill);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create skill");
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-surface border border-border rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-800">Create Custom Skill</h2>
          <button onClick={onClose} className="text-muted hover:text-slate-600 transition-colors">✕</button>
        </div>
        <div className="space-y-3">
          <div className="space-y-1">
            <label className="type-label">Name</label>
            <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="my-skill" />
          </div>
          <div className="space-y-1">
            <label className="type-label">Description</label>
            <input className={inputCls} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this skill does…" />
          </div>
          <div className="space-y-1">
            <label className="type-label">Content (Markdown)</label>
            <textarea
              className={`${inputCls} resize-none`}
              rows={8}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={"# Instructions\n\nDescribe the skill behaviour here…"}
            />
          </div>
        </div>
        {error && <p className="text-xs text-red-500">{error}</p>}
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-3 py-1.5 text-xs text-muted hover:text-slate-600 transition-colors">Cancel</button>
          <button
            onClick={handleCreate}
            disabled={loading || !name.trim() || !description.trim() || !content.trim()}
            className="px-4 py-1.5 bg-accent hover:bg-accent-muted disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-xs font-medium transition-colors"
          >
            {loading ? "Creating…" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SkillsPage() {
  const [catalog, setCatalog] = useState<SkillCatalogEntry[]>([]);
  const [catalogMeta, setCatalogMeta] = useState<PageMeta | null>(null);
  const [catalogPage, setCatalogPage] = useState(1);
  const [catalogQ, setCatalogQ] = useState("");
  const debouncedCatalogQ = useDebounce(catalogQ, 300);
  const [catalogLoading, setCatalogLoading] = useState(true);

  const [skills, setSkills] = useState<Skill[]>([]);
  const [meta, setMeta] = useState<PageMeta | null>(null);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const debouncedQ = useDebounce(q, 300);
  const [loading, setLoading] = useState(true);

  const [showImport, setShowImport] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  const CATALOG_PAGE_SIZE = 12;
  const MY_PAGE_SIZE = 12;

  useEffect(() => {
    setCatalogLoading(true);
    api.listSkillsCatalog(debouncedCatalogQ || undefined, catalogPage, CATALOG_PAGE_SIZE)
      .then((r) => { setCatalog(r.items); setCatalogMeta(r.meta); })
      .catch(() => {})
      .finally(() => setCatalogLoading(false));
  }, [debouncedCatalogQ, catalogPage]);

  useEffect(() => { setCatalogPage(1); }, [debouncedCatalogQ]);

  useEffect(() => {
    setLoading(true);
    api.listSkills(debouncedQ || undefined, page, MY_PAGE_SIZE)
      .then((res) => { setSkills(res.items); setMeta(res.meta); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [debouncedQ, page]);

  useEffect(() => { setPage(1); }, [debouncedQ]);

  function handleDeleted(id: string) {
    setSkills((prev) => prev.filter((s) => s.id !== id));
    if (meta) setMeta({ ...meta, total: meta.total - 1 });
  }

  function handleAdded(skill: Skill) {
    setSkills((prev) => prev.some((s) => s.id === skill.id) ? prev : [skill, ...prev]);
    if (meta) setMeta({ ...meta, total: meta.total + 1 });
    if (skill.github_url) {
      setCatalog((prev) =>
        prev.map((e) => e.github_url === skill.github_url ? { ...e, imported: true } : e)
      );
    }
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border px-6 py-4 bg-surface flex-shrink-0">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-base font-semibold text-slate-900">Skills</h1>
            <p className="text-xs text-muted mt-0.5">Reusable instructions injected into agent system prompts at runtime.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowImport(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-border bg-surface hover:bg-bg text-xs font-medium text-slate-700 rounded-lg transition-colors"
            >
              <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5">
                <path d="M8 1v9M4 6l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M1 13h14" strokeLinecap="round" />
              </svg>
              Import URL
            </button>
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent-muted text-white text-xs font-medium rounded-lg transition-colors"
            >
              <svg viewBox="0 0 16 16" fill="none" className="w-3.5 h-3.5">
                <path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
              </svg>
              New Skill
            </button>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-6 py-5 space-y-8">

        {/* Anthropic catalog */}
        <section>
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Anthropic Skills</h2>
            <Input
              value={catalogQ}
              onChange={(e) => setCatalogQ(e.target.value)}
              placeholder="Search…"
              className="w-44"
            />
            {catalogMeta && (
              <span className="text-[11px] text-muted ml-auto">{catalogMeta.total} skills</span>
            )}
          </div>

          {catalogLoading ? (
            <div className="flex justify-center py-10"><Spinner /></div>
          ) : catalog.length === 0 ? (
            <p className="text-xs text-muted py-4">No results for "{catalogQ}".</p>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {catalog.map((entry) => (
                  <CatalogCard key={entry.github_url} entry={entry} onImported={handleAdded} />
                ))}
              </div>
              {catalogMeta && catalogMeta.pages > 1 && (
                <div className="mt-4">
                  <Pagination meta={catalogMeta} onChange={setCatalogPage} />
                </div>
              )}
            </>
          )}
        </section>

        {/* My skills */}
        <section>
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">My Skills</h2>
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search…"
              className="w-44"
            />
            {meta && (
              <span className="text-[11px] text-muted ml-auto">{meta.total} skill{meta.total !== 1 ? "s" : ""}</span>
            )}
          </div>

          {loading ? (
            <div className="flex justify-center py-10"><Spinner /></div>
          ) : skills.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center gap-2">
              <p className="text-sm text-slate-600 font-medium">
                {q ? "No skills match your search." : "No skills added yet."}
              </p>
              <p className="text-xs text-muted max-w-xs">
                {q ? "Try a different term." : "Add an Anthropic skill above, import a GitHub URL, or create your own."}
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {skills.map((sk) => (
                  <SkillCard key={sk.id} skill={sk} onDelete={handleDeleted} />
                ))}
              </div>
              {meta && meta.pages > 1 && (
                <div className="mt-4">
                  <Pagination meta={meta} onChange={setPage} />
                </div>
              )}
            </>
          )}
        </section>
      </div>

      {showImport && (
        <ImportGithubModal onImported={handleAdded} onClose={() => setShowImport(false)} />
      )}

      {showCreate && (
        <CreateCustomModal onCreated={handleAdded} onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
}
