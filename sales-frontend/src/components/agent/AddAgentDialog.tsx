import { useState } from "react";
import Dialog from "../Dialog";
import { inputCls } from "./types";
import type { Agent } from "../../types";
import SearchableSelect from "../SearchableSelect";

interface AddAgentDialogProps {
  availableAgents: Agent[];
  onAdd: (agent: Agent, usage: string) => void;
  onClose: () => void;
}

export default function AddAgentDialog({ availableAgents, onAdd, onClose }: AddAgentDialogProps) {
  const [selectedId, setSelectedId] = useState("");
  const [usage, setUsage] = useState("");
  const [err, setErr] = useState("");

  function add() {
    const picked = availableAgents.find((a) => a.id === selectedId);
    if (!picked) { setErr("Select an agent"); return; }
    if (!usage.trim()) { setErr("Enter a usage description"); return; }
    onAdd(picked, usage.trim());
    onClose();
  }

  const footer = (
    <>
      <button onClick={onClose} className="flex-1 py-2 border border-border rounded-lg text-sm text-muted hover:bg-bg transition-colors">Cancel</button>
      <button onClick={add} className="flex-1 py-2 bg-accent hover:bg-accent-muted text-white rounded-lg text-sm font-medium transition-colors">Add</button>
    </>
  );

  return (
    <Dialog title="Add Managed Agent" size="md" onClose={onClose} footer={footer}>
      <div className="space-y-3">
        <div>
          <label className="type-label block mb-1.5">Agent</label>
          <SearchableSelect
            options={availableAgents.map((a) => ({ value: a.id, label: a.name || a.role, description: a.role !== a.name ? a.role : undefined }))}
            value={selectedId}
            onChange={setSelectedId}
            placeholder="— Select an agent —"
            searchPlaceholder="Search agents…"
            emptyMessage="No agents found"
            emptyLabel=""
          />
        </div>
        <div>
          <label className="type-label block mb-1.5">When to use this agent</label>
          <input
            value={usage}
            onChange={(e) => setUsage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && add()}
            placeholder="e.g. Use for pricing questions"
            className={inputCls}
          />
        </div>
        {err && <p className="text-xs text-red-500">{err}</p>}
      </div>
    </Dialog>
  );
}
