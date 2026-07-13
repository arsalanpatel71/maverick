import { useCallback, useEffect, useRef, useState } from "react";
import type { Agent, PageMeta, RAGItem, Skill, SkillCatalogEntry } from "../../types";
import type { FormState } from "./types";
import RAGSettingsPopover from "./RAGSettingsPopover";
import AddAgentDialog from "./AddAgentDialog";
import InfoTip from "./InfoTip";
import SearchableSelect from "../SearchableSelect";
import Spinner from "../Spinner";
import { api } from "../../api";
import { useDebounce } from "../../hooks/useDebounce";
import { skillColor, skillInitials } from "../../utils/skillColor";

// ── skill picker dialog ───────────────────────────────────────────────────────

const PAGE_SIZE = 10;

function useInfiniteSkills(fetcher: (q: string, page: number) => Promise<{ items: Skill[]; meta: PageMeta }>) {
  const [q, setQ] = useState("");
  const dq = useDebounce(q, 300);
  const [items, setItems] = useState<Skill[]>([]);
  const [page, setPage] = useState(1);
  const [meta, setMeta] = useState<PageMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const prevQRef = useRef(dq);
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const isNewSearch = dq !== prevQRef.current;
    if (isNewSearch) {
      prevQRef.current = dq;
      if (page !== 1) { setPage(1); setItems([]); return; }
      setItems([]);
    }
    let cancelled = false;
    setLoading(true);
    fetcher(dq, page)
      .then((res) => {
        if (cancelled) return;
        setItems((prev) => (page === 1 || isNewSearch) ? res.items : [...prev, ...res.items]);
        setMeta(res.meta);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [dq, page]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !loading && meta && page < meta.pages) setPage((p) => p + 1);
    }, { threshold: 0.1 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [loading, meta, page]);

  return { q, setQ, items, meta, loading, sentinelRef };
}

function SkillRow({
  name, description, selected, loading: rowLoading, onClick,
}: {
  name: string; description: string; selected: boolean; loading?: boolean; onClick: () => void;
}) {
  return (
    <li
      onClick={onClick}
      className="flex items-center gap-3 px-4 py-3 hover:bg-bg cursor-pointer transition-colors select-none"
    >
      <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 uppercase transition-all duration-150 ${selected ? "bg-accent text-white shadow-sm" : skillColor(name)}`}>
        {rowLoading ? (
          <div className="w-3.5 h-3.5 border-2 border-white/60 border-t-white rounded-full animate-spin" />
        ) : selected ? (
          <svg viewBox="0 0 16 16" fill="none" className="w-4 h-4">
            <path d="M3 8l4 4 6-7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : skillInitials(name)}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-xs font-medium truncate transition-colors ${selected ? "text-accent" : "text-slate-800"}`}>{name}</p>
        <p className="text-[11px] text-muted mt-0.5 line-clamp-1">{description}</p>
      </div>
    </li>
  );
}

function AnthropicTab({
  localAttached, onToggle,
}: {
  localAttached: Set<string>;
  onToggle: (skill: Skill, add: boolean) => void;
}) {
  const [catalogItems, setCatalogItems] = useState<SkillCatalogEntry[]>([]);
  const [catalogMeta, setCatalogMeta] = useState<PageMeta | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogPage, setCatalogPage] = useState(1);
  const [q, setQ] = useState("");
  const dq = useDebounce(q, 300);
  const prevQRef = useRef(dq);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [importing, setImporting] = useState<string | null>(null); // github_url being imported

  useEffect(() => {
    const isNewSearch = dq !== prevQRef.current;
    if (isNewSearch) {
      prevQRef.current = dq;
      if (catalogPage !== 1) { setCatalogPage(1); setCatalogItems([]); return; }
      setCatalogItems([]);
    }
    let cancelled = false;
    setCatalogLoading(true);
    api.listSkillsCatalog(dq || undefined, catalogPage, PAGE_SIZE)
      .then((res) => {
        if (cancelled) return;
        setCatalogItems((prev) => (catalogPage === 1 || isNewSearch) ? res.items : [...prev, ...res.items]);
        setCatalogMeta(res.meta);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setCatalogLoading(false); });
    return () => { cancelled = true; };
  }, [dq, catalogPage]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !catalogLoading && catalogMeta && catalogPage < catalogMeta.pages)
        setCatalogPage((p) => p + 1);
    }, { threshold: 0.1 });
    obs.observe(el);
    return () => obs.disconnect();
  }, [catalogLoading, catalogMeta, catalogPage]);

  async function handleCatalogClick(entry: SkillCatalogEntry) {
    // If already attached (we know its skill_id), just detach
    if (entry.skill_id && localAttached.has(entry.skill_id)) {
      const partialSkill = { id: entry.skill_id, name: entry.name, description: entry.description, content: "", source: "github" as const, github_url: entry.github_url, owner_id: null, created_at: "", updated_at: "" };
      onToggle(partialSkill, false);
      return;
    }
    // If already imported (has DB id) but not attached, just attach
    if (entry.skill_id) {
      const partialSkill = { id: entry.skill_id, name: entry.name, description: entry.description, content: "", source: "github" as const, github_url: entry.github_url, owner_id: null, created_at: "", updated_at: "" };
      onToggle(partialSkill, true);
      return;
    }
    // Not yet imported — import then attach
    setImporting(entry.github_url);
    try {
      const skill = await api.importSkillFromGithub(entry.github_url);
      // Update this entry's skill_id locally so subsequent clicks work correctly
      setCatalogItems((prev) => prev.map((e) => e.github_url === entry.github_url ? { ...e, imported: true, skill_id: skill.id } : e));
      onToggle(skill, true);
    } catch {
      // silently ignore — user can retry
    } finally {
      setImporting(null);
    }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden min-h-0">
      <div className="px-4 py-2.5 border-b border-border flex-shrink-0">
        <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search Anthropic skills…"
          className="w-full bg-bg border border-border rounded-lg px-3 py-1.5 text-xs text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light transition-colors" />
      </div>
      <div className="flex-1 overflow-y-auto scrollbar-thin min-h-0">
        {catalogItems.length === 0 && catalogLoading ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : catalogItems.length === 0 ? (
          <p className="text-xs text-muted text-center py-10">No skills match.</p>
        ) : (
          <ul className="divide-y divide-border">
            {catalogItems.map((entry) => {
              const selected = !!(entry.skill_id && localAttached.has(entry.skill_id));
              return (
                <SkillRow
                  key={entry.github_url}
                  name={entry.name}
                  description={entry.description}
                  selected={selected}
                  loading={importing === entry.github_url}
                  onClick={() => handleCatalogClick(entry)}
                />
              );
            })}
          </ul>
        )}
        <div ref={sentinelRef} className="h-8 flex items-center justify-center">
          {catalogLoading && catalogItems.length > 0 && <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />}
        </div>
      </div>
    </div>
  );
}

function MySkillsTab({
  localAttached, onToggle,
}: {
  localAttached: Set<string>;
  onToggle: (skill: Skill, add: boolean) => void;
}) {
  const { q, setQ, items, meta, loading, sentinelRef } = useInfiniteSkills(
    (searchQ, p) => api.listSkills(searchQ || undefined, p, PAGE_SIZE),
  );

  return (
    <div className="flex flex-col flex-1 overflow-hidden min-h-0">
      <div className="px-4 py-2.5 border-b border-border flex-shrink-0">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search my skills…"
          className="w-full bg-bg border border-border rounded-lg px-3 py-1.5 text-xs text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light transition-colors" />
      </div>
      <div className="flex-1 overflow-y-auto scrollbar-thin min-h-0">
        {items.length === 0 && loading ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : items.length === 0 ? (
          <p className="text-xs text-muted text-center py-10">
            {q ? "No skills match." : "No imported skills yet. Try the Anthropic tab."}
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {items.map((sk) => {
              const selected = localAttached.has(sk.id);
              return (
                <SkillRow
                  key={sk.id}
                  name={sk.name}
                  description={sk.description}
                  selected={selected}
                  onClick={() => onToggle(sk, !selected)}
                />
              );
            })}
          </ul>
        )}
        <div ref={sentinelRef} className="h-8 flex items-center justify-center">
          {loading && items.length > 0 && <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />}
        </div>
        {meta && <p className="text-[10px] text-muted text-center pb-2">{meta.total} skill{meta.total !== 1 ? "s" : ""}</p>}
      </div>
    </div>
  );
}

function SkillPickerDialog({
  attachedIds,
  onToggle,
  onClose,
}: {
  attachedIds: string[];
  onToggle: (skill: Skill, add: boolean) => void;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"anthropic" | "mine">("anthropic");
  const [localAttached, setLocalAttached] = useState(() => new Set(attachedIds));

  function handleToggle(skill: Skill, add: boolean) {
    setLocalAttached((prev) => {
      const next = new Set(prev);
      add ? next.add(skill.id) : next.delete(skill.id);
      return next;
    });
    onToggle(skill, add);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-surface border border-border rounded-2xl shadow-2xl w-full max-w-sm mx-4 flex flex-col overflow-hidden"
        style={{ maxHeight: "72vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3.5 border-b border-border flex-shrink-0">
          <h2 className="text-sm font-semibold text-slate-900">Add Skills</h2>
          <button onClick={onClose} className="text-muted hover:text-slate-700 transition-colors text-lg leading-none">✕</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border flex-shrink-0">
          {(["anthropic", "mine"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors relative ${tab === t ? "text-accent" : "text-muted hover:text-slate-600"}`}
            >
              {t === "anthropic" ? "Anthropic Skills" : "My Skills"}
              {tab === t && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex flex-col flex-1 overflow-hidden min-h-0">
          {tab === "anthropic"
            ? <AnthropicTab localAttached={localAttached} onToggle={handleToggle} />
            : <MySkillsTab localAttached={localAttached} onToggle={handleToggle} />}
        </div>

        {/* Footer */}
        <div className="border-t border-border px-4 py-3 flex items-center justify-between flex-shrink-0 bg-surface">
          <span className="text-xs text-muted">{localAttached.size} selected</span>
          <button onClick={onClose} className="px-4 py-1.5 bg-accent hover:bg-accent-muted text-white text-xs font-medium rounded-lg transition-colors">
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

// ── panel props / component ───────────────────────────────────────────────────

interface AttachmentsPanelProps {
  form: FormState;
  setForm: (updater: ((prev: FormState) => FormState) | FormState) => void;
  rags: RAGItem[];
  allAgents: Agent[];
  skills: Skill[];
  agentId: string | null;
  readOnly?: boolean;
}

export default function AttachmentsPanel({ form, setForm, rags, allAgents, skills, agentId, readOnly }: AttachmentsPanelProps) {
  const [ragEnabled, setRagEnabled] = useState(!!form.rag_id);
  const [showRagSettings, setShowRagSettings] = useState(false);
  const [settingsPos, setSettingsPos] = useState({ top: 0, left: 0 });
  const [showAddAgent, setShowAddAgent] = useState(false);
  const [showSkillPicker, setShowSkillPicker] = useState(false);
  const settingsBtnRef = useRef<HTMLButtonElement>(null);
  const closeRagSettings = useCallback(() => setShowRagSettings(false), []);

  // Keep a map of known skill objects so chips always have their full data
  // even for skills added through the picker (not in the initial props list).
  const [knownSkills, setKnownSkills] = useState<Map<string, Skill>>(
    () => new Map(skills.map((s) => [s.id, s])),
  );
  useEffect(() => {
    setKnownSkills((prev) => {
      const next = new Map(prev);
      skills.forEach((s) => next.set(s.id, s));
      return next;
    });
  }, [skills]);

  function openSettings() {
    if (settingsBtnRef.current) {
      const r = settingsBtnRef.current.getBoundingClientRect();
      setSettingsPos({ top: r.bottom + 4, left: r.right - 256 });
    }
    setShowRagSettings((p) => !p);
  }

  function toggleRag() {
    if (ragEnabled) {
      setRagEnabled(false);
      setShowRagSettings(false);
      setField("rag_id", "");
    } else {
      setRagEnabled(true);
    }
  }

  const availableAgents = allAgents.filter(
    (a) => a.id !== agentId && !form.managed_agents.some((m) => m.id === a.id),
  );

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function handleSkillToggle(skill: Skill, add: boolean) {
    setKnownSkills((prev) => new Map(prev).set(skill.id, skill));
    const next = add
      ? [...form.skill_ids, skill.id]
      : form.skill_ids.filter((id) => id !== skill.id);
    setField("skill_ids", next);
  }

  return (
    <fieldset disabled={readOnly} className="flex flex-col h-full overflow-hidden disabled:opacity-60 disabled:pointer-events-none">
      <div className="px-4 py-3 border-b border-border bg-surface flex-shrink-0">
        <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wide">Attachments</h3>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {/* RAG */}
        <div className="p-4 border-b border-border space-y-2.5">
          <div className="flex items-center justify-between">
            <label className="type-label flex items-center">
              Knowledge Base
              <InfoTip text="Connect a RAG knowledge base so the agent searches documents before responding." />
            </label>
            <button
              type="button"
              onClick={toggleRag}
              className={`relative w-9 h-[18px] rounded-full transition-colors flex-shrink-0 ${ragEnabled ? "bg-accent" : "bg-border"}`}
            >
              <span className={`absolute top-[1px] w-3.5 h-3.5 rounded-full bg-white shadow transition-all ${ragEnabled ? "left-[20px]" : "left-[1px]"}`} />
            </button>
          </div>

          {ragEnabled && (
            <div className="flex gap-2 items-start">
              <SearchableSelect
                className="flex-1"
                size="sm"
                options={rags.map((r) => ({ value: r.id, label: r.name, description: r.embedding_model }))}
                value={form.rag_id}
                onChange={(v) => { if (v) setField("rag_id", v); }}
                placeholder="Select knowledge base…"
                searchPlaceholder="Search knowledge bases…"
                emptyMessage="No knowledge bases found"
                emptyLabel=""
              />
              {form.rag_id && (
                <button
                  ref={settingsBtnRef}
                  type="button"
                  onClick={openSettings}
                  className={`flex-shrink-0 px-2.5 py-1.5 border rounded-lg text-sm transition-colors ${showRagSettings ? "bg-accent-faint border-accent-light text-accent" : "bg-surface border-border text-muted hover:text-slate-600 hover:border-accent-light/50"}`}
                >⚙</button>
              )}
            </div>
          )}

          {ragEnabled && !form.rag_id && (
            <p className="text-xs text-muted">Select a knowledge base above.</p>
          )}

          {showRagSettings && (
            <RAGSettingsPopover
              settings={form.rag_settings}
              onChange={(s) => setForm((f) => ({ ...f, rag_settings: s }))}
              onClose={closeRagSettings}
              position={settingsPos}
            />
          )}
        </div>

        {/* Skills */}
        <div className="p-4 border-b border-border space-y-2.5">
          <div className="flex items-center justify-between">
            <label className="type-label flex items-center">
              Skills
              <InfoTip text="Attach skills to inject specialised instructions into this agent's system prompt at runtime." />
            </label>
            <button
              type="button"
              onClick={() => setShowSkillPicker(true)}
              className="flex items-center gap-1 text-xs font-medium text-accent hover:text-accent-muted transition-colors"
            >
              <svg viewBox="0 0 16 16" fill="none" className="w-3 h-3">
                <path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
              </svg>
              Add
            </button>
          </div>

          {form.skill_ids.length === 0 ? (
            <p className="text-xs text-muted">No skills attached.</p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {form.skill_ids.map((id) => {
                const sk = knownSkills.get(id);
                if (!sk) return null;
                return (
                  <div
                    key={id}
                    className="flex items-center gap-2.5 bg-accent-faint border border-accent-light/60 rounded-lg px-2.5 py-1.5"
                  >
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-[10px] flex-shrink-0 uppercase ${skillColor(sk.name)}`}>
                      {skillInitials(sk.name)}
                    </div>
                    <p className="flex-1 text-xs font-medium text-accent truncate">{sk.name}</p>
                    <button
                      type="button"
                      onClick={() => setField("skill_ids", form.skill_ids.filter((i) => i !== id))}
                      className="flex-shrink-0 text-accent/50 hover:text-red-500 transition-colors"
                      title="Remove skill"
                    >
                      <svg viewBox="0 0 12 12" fill="none" className="w-3 h-3">
                        <path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Managed Agents */}
        <div className="p-4 space-y-2.5">
          <div className="flex items-center justify-between">
            <label className="type-label flex items-center">
              Agents
              <InfoTip text="Add child agents to delegate tasks to — this turns the current agent into a manager that routes requests intelligently." />
            </label>
            {availableAgents.length > 0 && (
              <button
                type="button"
                onClick={() => setShowAddAgent(true)}
                className="flex items-center gap-1 text-xs font-medium text-accent hover:text-accent-muted transition-colors"
              >
                <svg viewBox="0 0 16 16" fill="none" className="w-3 h-3">
                  <path d="M8 2v12M2 8h12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
                </svg>
                Add
              </button>
            )}
          </div>

          {form.managed_agents.length > 0 ? (
            <div className="space-y-2">
              {form.managed_agents.map((ma) => (
                <div key={ma.id} className="flex items-start gap-2.5 bg-bg border border-border rounded-lg px-3 py-2.5">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-700 truncate">{ma.name}</p>
                    <p className="text-[11px] text-muted mt-0.5 leading-relaxed">{ma.usage_description}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setField("managed_agents", form.managed_agents.filter((a) => a.id !== ma.id))}
                    className="flex-shrink-0 text-muted hover:text-red-500 transition-colors mt-0.5 text-sm"
                  >✕</button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted">
              {availableAgents.length === 0
                ? "Create more agents first to set up delegation."
                : "No agents added yet."}
            </p>
          )}
        </div>
      </div>

      {showAddAgent && (
        <AddAgentDialog
          availableAgents={availableAgents}
          onAdd={(a, usage) => setField("managed_agents", [
            ...form.managed_agents,
            { id: a.id, name: a.name || a.role, usage_description: usage },
          ])}
          onClose={() => setShowAddAgent(false)}
        />
      )}

      {showSkillPicker && (
        <SkillPickerDialog
          attachedIds={form.skill_ids}
          onToggle={handleSkillToggle}
          onClose={() => setShowSkillPicker(false)}
        />
      )}
    </fieldset>
  );
}
