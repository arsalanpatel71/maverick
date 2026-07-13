import { useEffect } from "react";
import { createPortal } from "react-dom";
import type { RAGSettings } from "./types";

interface Props {
  settings: RAGSettings;
  onChange: (s: RAGSettings) => void;
  onClose: () => void;
  position: { top: number; left: number };
}

export default function RAGSettingsPopover({ settings, onChange, onClose, position }: Props) {
  function set<K extends keyof RAGSettings>(k: K, v: RAGSettings[K]) { onChange({ ...settings, [k]: v }); }
  useEffect(() => {
    function handleKey(e: KeyboardEvent) { if (e.key === "Escape") onClose(); }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);
  return createPortal(
    <div className="fixed inset-0 z-[90]" onClick={onClose}>
      <div style={{ top: position.top, left: position.left }} className="fixed bg-surface border border-border rounded-xl shadow-xl p-4 w-64 space-y-3 z-[100]" onClick={(e) => e.stopPropagation()}>
        <p className="text-xs font-semibold text-slate-700 uppercase tracking-wide">RAG Settings</p>
        <div>
          <label className="type-label-sm block mb-1">Retrieval type</label>
          <select value={settings.retrieval_type} onChange={(e) => set("retrieval_type", e.target.value)} className="w-full bg-bg border border-border rounded-lg px-2 py-1.5 text-xs text-slate-700">
            <option value="basic">Basic similarity</option>
            <option value="mmr">MMR (diversity)</option>
          </select>
        </div>
        {(
          [["Top K", "top_k"], ["Score Threshold", "score_threshold"], ["Lambda (MMR)", "lambda_param"], ["Time Decay", "time_decay_factor"]] as [string, keyof RAGSettings][]
        ).map(([label, key]) => (
          <div key={key}>
            <div className="flex justify-between mb-1">
              <label className="type-label-sm">{label}</label>
              <span className="text-[10px] font-mono text-accent">{settings[key]}</span>
            </div>
            <input type="range" min={key === "top_k" ? 1 : 0} max={key === "top_k" ? 50 : 1} step={key === "top_k" ? 1 : 0.05}
              value={settings[key] as number}
              onChange={(e) => set(key, key === "top_k" ? parseInt(e.target.value) : parseFloat(e.target.value))}
              className="w-full accent-accent" />
          </div>
        ))}
      </div>
    </div>,
    document.body
  );
}
