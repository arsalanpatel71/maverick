import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import type { Agent, ProviderModels } from "../../types";
import { inputCls, selectCls, formsEqual, formFromAgent } from "./types";
import type { FormState } from "./types";
import InfoTip from "./InfoTip";
import SchemaDialog from "./SchemaDialog";
import Dialog from "../Dialog";

// ── ExpandableTextarea ────────────────────────────────────────────────────────

const ExpandIcon = () => (
  <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M10 2h4v4M14 2l-5 5M6 14H2v-4M2 14l5-5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

interface ExpandableTextareaProps {
  label: string;
  required?: boolean;
  infotip?: string;
  value: string;
  onChange: (v: string) => void;
  rows?: number;
  placeholder?: string;
  mono?: boolean;
  spellCheck?: boolean;
  dialogMinHeight?: string;
  agentName?: string;
  headerExpand?: boolean; // button in label row (instructions); false = overlaid top-right (role/goal)
}

function ExpandableTextarea({
  label, required, infotip, value, onChange,
  rows = 3, placeholder, mono, spellCheck,
  dialogMinHeight = "200px", agentName, headerExpand,
}: ExpandableTextareaProps) {
  const [draft, setDraft] = useState<string | null>(null);

  const canExpand = headerExpand ? value.trim().length > 0 : true;

  const expandBtn = canExpand ? (
    <button
      type="button"
      onClick={() => setDraft(value)}
      title="Expand"
      className={
        headerExpand
          ? "flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors"
          : "absolute top-2 right-2 text-muted hover:text-accent transition-colors"
      }
    >
      <ExpandIcon />
      {headerExpand && <span>Expand</span>}
    </button>
  ) : null;

  return (
    <div>
      <div className={`flex items-center ${headerExpand ? "justify-between" : ""} mb-1.5`}>
        <label className="type-label block">
          {label} {required && <span className="text-red-500 normal-case font-normal">*</span>}
          {infotip && <InfoTip text={infotip} />}
        </label>
        {headerExpand && expandBtn}
      </div>

      <div className={!headerExpand ? "relative" : undefined}>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={rows}
          className={`${inputCls} resize-none${!headerExpand ? " pr-8" : ""}${mono ? " font-mono leading-relaxed" : ""}`}
          placeholder={placeholder}
          spellCheck={spellCheck}
        />
        {!headerExpand && expandBtn}
      </div>

      {draft !== null && (
        <Dialog
          title={label}
          subtitle={agentName || undefined}
          size="lg"
          onClose={() => setDraft(null)}
          footer={
            <>
              <div className="flex-1" />
              <button
                onClick={() => { onChange(draft); setDraft(null); }}
                className="px-3 py-1.5 bg-accent hover:bg-accent-muted text-white rounded-lg text-xs font-medium transition-colors"
              >
                Save
              </button>
            </>
          }
        >
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            style={{ minHeight: dialogMinHeight }}
            className={`w-full h-full bg-bg border border-border rounded-lg px-3 py-3 text-sm text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors resize-none leading-relaxed${mono ? " font-mono" : ""}`}
            placeholder={placeholder}
            spellCheck={spellCheck}
            autoFocus
          />
        </Dialog>
      )}
    </div>
  );
}

// ── AgentForm ─────────────────────────────────────────────────────────────────

interface AgentFormProps {
  form: FormState;
  onFormChange: (f: FormState) => void;
  savedForm: FormState;
  onSavedFormChange: (f: FormState) => void;
  agent: Agent | null;
  providers: ProviderModels[];
  isNew: boolean;
  readOnly?: boolean;
  onCreated: (a: Agent) => void;
  onSaved: (a: Agent) => void;
  onSavingChange: (v: boolean) => void;
  onJustSavedChange: (v: boolean) => void;
  onSaveErrorChange: (v: string | null) => void;
  doSaveRef: { current: (() => void) | null };
}

export default function AgentForm({
  form, onFormChange, savedForm, onSavedFormChange,
  agent, providers, isNew, readOnly,
  onCreated, onSaved,
  onSavingChange, onJustSavedChange, onSaveErrorChange,
  doSaveRef,
}: AgentFormProps) {
  const [saving, setSavingState] = useState(false);
  const [saveError, setSaveErrorState] = useState<string | null>(null);
  const [showSchemaDialog, setShowSchemaDialog] = useState(false);
  const navigate = useNavigate();

  function setSaving(v: boolean) { setSavingState(v); onSavingChange(v); }
  function setSaveError(v: string | null) { setSaveErrorState(v); onSaveErrorChange(v); }
  function setJustSaved(v: boolean) { onJustSavedChange(v); }

  const isDirty = !isNew && !formsEqual(form, savedForm);
  const currentModels = providers.find((p) => p.provider === form.provider)?.models ?? [];

  doSaveRef.current = () => { if (isNew) handleCreate(); else handleSave(); };

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    onFormChange({ ...form, [key]: value });
    setJustSaved(false);
  }

  function handleProviderChange(provider: string) {
    const models = providers.find((p) => p.provider === provider)?.models ?? [];
    onFormChange({ ...form, provider, model: models[0]?.id ?? "" });
    setJustSaved(false);
  }

  function buildPayload() {
    let response_schema = null;
    if (form.schema_enabled && form.schema_name.trim() && form.schema_json.trim()) {
      try {
        response_schema = {
          name: form.schema_name.trim(),
          description: form.schema_desc.trim() || null,
          json_schema: JSON.parse(form.schema_json),
        };
      } catch {}
    }
    return {
      name: form.name, role: form.role, goal: form.goal, instructions: form.instructions,
      provider: form.provider, model: form.model,
      memory_enabled: form.memory_enabled,
      memory_max_messages: form.memory_enabled ? form.memory_max_messages : null,
      rag_config: form.rag_id ? { rag_ids: [form.rag_id], ...form.rag_settings } : null,
      managed_agents: form.managed_agents,
      response_schema,
      skill_ids: form.skill_ids,
    };
  }

  async function handleCreate() {
    if (!form.name.trim() || !form.role.trim() || !form.goal.trim() || !form.instructions.trim()) {
      setSaveError("Name, role, goal, and instructions are required.");
      return;
    }
    setSaving(true); setSaveError(null);
    try {
      const created = await api.createAgent(buildPayload());
      onCreated(created);
      navigate(`/agents/${created.id}`, { replace: true });
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSave() {
    setSaving(true); setSaveError(null);
    try {
      const updated = await api.updateAgent(agent!.id, buildPayload());
      onSaved(updated);
      const newForm = formFromAgent(updated);
      onSavedFormChange(newForm);
      onFormChange(newForm);
      setJustSaved(true);
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <fieldset disabled={readOnly} className="space-y-4 disabled:opacity-60 disabled:pointer-events-none">
      {readOnly && (
        <div className="flex items-center gap-2 px-3 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-3.5 h-3.5 flex-shrink-0">
            <rect x="3" y="7" width="10" height="7" rx="1.5"/>
            <path d="M5 7V5a3 3 0 0 1 6 0v2"/>
          </svg>
          <span className="font-medium">You have been given read access only — editing is disabled.</span>
        </div>
      )}

      {/* Name */}
      <div>
        <label className="type-label block mb-1.5">
          Name {isNew && <span className="text-red-500 normal-case font-normal">*</span>}
          <InfoTip text="A short display name for this agent, shown in the agent list and navbar." />
        </label>
        <input
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          className={inputCls}
          placeholder="e.g. Support Agent"
        />
      </div>

      {/* Role */}
      <ExpandableTextarea
        label="Role"
        required={isNew}
        infotip="The agent's persona — injected into the system prompt to shape its tone and expertise."
        value={form.role}
        onChange={(v) => set("role", v)}
        rows={3}
        placeholder="e.g. Customer Support Specialist"
        agentName={form.name}
      />

      {/* Provider + Model */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="type-label block mb-1.5">
            Provider
            <InfoTip text="The AI provider that powers this agent's language model." />
          </label>
          <select value={form.provider} onChange={(e) => handleProviderChange(e.target.value)} className={selectCls}>
            {providers.map((p) => (
              <option key={p.provider} value={p.provider}>
                {p.provider.charAt(0).toUpperCase() + p.provider.slice(1)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="type-label block mb-1.5">
            Model
            <InfoTip text="The specific model version. Different models trade off cost, speed, and capability." />
          </label>
          <select value={form.model} onChange={(e) => set("model", e.target.value)} className={`${selectCls} font-mono`}>
            {currentModels.map((m) => (
              <option key={m.id} value={m.id} title={m.description}>{m.id}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Goal */}
      <ExpandableTextarea
        label="Goal"
        required={isNew}
        infotip="A concise statement of what this agent is trying to accomplish — helps the model stay on task."
        value={form.goal}
        onChange={(v) => set("goal", v)}
        rows={3}
        placeholder="What is this agent trying to accomplish?"
        agentName={form.name}
      />

      {/* Instructions */}
      <ExpandableTextarea
        label="Instructions"
        required={isNew}
        infotip="The system prompt — detailed rules, tone, and behavior guidelines. Supports plain text or markdown."
        value={form.instructions}
        onChange={(v) => set("instructions", v)}
        rows={7}
        placeholder="System prompt / instructions for the agent…"
        mono
        spellCheck={false}
        dialogMinHeight="400px"
        agentName={form.name}
        headerExpand
      />

      {/* Memory */}
      <div className="bg-surface border border-border rounded-xl px-4 py-3 space-y-2">
        <div className="flex items-center justify-between gap-3">
          <label className="type-label flex items-center">
            Memory
            <InfoTip text="When enabled, the agent retains recent messages within the same session for conversational context." />
          </label>
          <button
            onClick={() => set("memory_enabled", !form.memory_enabled)}
            className={`relative w-9 h-[18px] rounded-full transition-colors flex-shrink-0 overflow-hidden ${form.memory_enabled ? "bg-accent" : "bg-border"}`}
          >
            <span className={`absolute top-[1px] w-3.5 h-3.5 rounded-full bg-white shadow transition-all ${form.memory_enabled ? "left-[20px]" : "left-[1px]"}`} />
          </button>
        </div>
        {form.memory_enabled && (
          <div>
            <div className="flex justify-between mb-1">
              <span className="text-xs text-muted">Max messages</span>
              <span className="text-xs font-mono text-accent font-medium">{form.memory_max_messages}</span>
            </div>
            <input
              type="range" min={1} max={50}
              value={form.memory_max_messages}
              onChange={(e) => set("memory_max_messages", parseInt(e.target.value))}
              className="w-full accent-accent"
            />
            <div className="flex justify-between type-caption mt-0.5"><span>1</span><span>50</span></div>
          </div>
        )}
      </div>

      {/* Structured JSON */}
      <div className="bg-surface border border-border rounded-xl px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex-1 min-w-0">
            <label className="type-label flex items-center">
              Structured JSON
              <InfoTip text="Force the agent to return structured JSON matching your schema. Works natively on OpenAI and Gemini; falls back to instruction-based for Anthropic and Perplexity." />
            </label>
            {form.schema_enabled && form.schema_name && (
              <div className="flex items-center gap-2 mt-1.5">
                <span className="text-xs font-mono text-accent truncate">{form.schema_name}</span>
                <button
                  type="button"
                  onClick={() => setShowSchemaDialog(true)}
                  className="text-xs text-muted hover:text-accent transition-colors flex-shrink-0"
                >
                  Edit
                </button>
              </div>
            )}
          </div>
          <button
            onClick={() => {
              if (!form.schema_enabled) { set("schema_enabled", true); setShowSchemaDialog(true); }
              else { set("schema_enabled", false); }
            }}
            className={`relative w-9 h-[18px] rounded-full transition-colors flex-shrink-0 overflow-hidden ${form.schema_enabled ? "bg-accent" : "bg-border"}`}
          >
            <span className={`absolute top-[1px] w-3.5 h-3.5 rounded-full bg-white shadow transition-all ${form.schema_enabled ? "left-[20px]" : "left-[1px]"}`} />
          </button>
        </div>
      </div>

      {showSchemaDialog && (
        <SchemaDialog
          initialName={form.schema_name}
          initialDesc={form.schema_desc}
          initialJson={form.schema_json}
          onSave={(name, desc, json) => {
            onFormChange({ ...form, schema_name: name, schema_desc: desc, schema_json: json });
            setJustSaved(false);
          }}
          onClose={() => setShowSchemaDialog(false)}
        />
      )}

      {saveError && <p className="text-xs text-red-600 pt-1">{saveError}</p>}

      {isDirty && !readOnly && (
        <div className="flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-2">
          <span className="text-amber-500 text-sm">⚠</span>
          <p className="text-amber-700 text-xs flex-1">You have unsaved changes.</p>
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-xs text-amber-600 font-medium underline underline-offset-2 hover:text-amber-700 transition-colors disabled:opacity-50"
          >
            Save now
          </button>
        </div>
      )}
    </fieldset>
  );
}
