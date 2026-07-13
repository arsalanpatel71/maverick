import { useState } from "react";
import Dialog from "../Dialog";
import { inputCls } from "./types";

interface SchemaDialogProps {
  initialName: string;
  initialDesc: string;
  initialJson: string;
  onSave: (name: string, desc: string, json: string) => void;
  onClose: () => void;
}

export default function SchemaDialog({ initialName, initialDesc, initialJson, onSave, onClose }: SchemaDialogProps) {
  const [name, setName] = useState(initialName);
  const [desc, setDesc] = useState(initialDesc);
  const [json, setJson] = useState(initialJson);
  const [validated, setValidated] = useState<null | "valid" | "invalid">(null);
  const [validErr, setValidErr] = useState("");
  const [saveErr, setSaveErr] = useState("");

  function validate() {
    if (!json.trim()) { setValidated("invalid"); setValidErr("JSON is empty"); return; }
    try { JSON.parse(json); setValidated("valid"); setValidErr(""); }
    catch (e) { setValidated("invalid"); setValidErr((e as Error).message); }
  }

  function save() {
    if (!name.trim()) { setSaveErr("Schema name is required"); return; }
    if (json.trim()) {
      try { JSON.parse(json); }
      catch (e) { setSaveErr("Fix JSON errors before saving: " + (e as Error).message); return; }
    }
    onSave(name.trim(), desc.trim(), json);
    onClose();
  }

  const footer = (
    <>
      <button onClick={validate} className="px-3 py-1.5 border border-border rounded-lg text-xs font-medium text-slate-600 hover:bg-bg transition-colors">
        Validate
      </button>
      <div className="flex-1" />
      <button onClick={onClose} className="px-3 py-1.5 border border-border rounded-lg text-xs font-medium text-muted hover:bg-bg transition-colors">Cancel</button>
      <button onClick={save} className="px-3 py-1.5 bg-accent hover:bg-accent-muted text-white rounded-lg text-xs font-medium transition-colors">Save</button>
    </>
  );

  return (
    <Dialog title="Structured JSON Schema" size="lg" onClose={onClose} footer={footer}>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="type-label block mb-1.5">Schema name <span className="text-red-500 font-normal">*</span></label>
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} placeholder="e.g. ExtractedData" autoFocus />
          </div>
          <div>
            <label className="type-label block mb-1.5">Description <span className="font-normal normal-case text-muted">(optional)</span></label>
            <input value={desc} onChange={(e) => setDesc(e.target.value)} className={inputCls} placeholder="What this schema captures" />
          </div>
        </div>
        <div>
          <label className="type-label block mb-1.5">JSON Schema</label>
          <textarea
            value={json}
            onChange={(e) => { setJson(e.target.value); setValidated(null); setSaveErr(""); }}
            rows={12}
            spellCheck={false}
            placeholder={'{\n  "type": "object",\n  "properties": {\n    "name": { "type": "string" }\n  },\n  "required": ["name"]\n}'}
            className={`w-full bg-bg border rounded-lg px-3 py-2.5 text-xs font-mono text-slate-800 placeholder-muted focus:outline-none focus:ring-2 transition-colors resize-none leading-relaxed ${validated === "invalid" ? "border-red-400 focus:border-red-400 focus:ring-red-200/30" : "border-border focus:border-accent-light focus:ring-accent-light/20"}`}
          />
          {validated === "valid" && <p className="mt-1 text-xs text-emerald-600">✓ Valid JSON</p>}
          {validated === "invalid" && <p className="mt-1 text-xs text-red-500 font-mono">{validErr}</p>}
        </div>
        {saveErr && <p className="text-xs text-red-500">{saveErr}</p>}
      </div>
    </Dialog>
  );
}
