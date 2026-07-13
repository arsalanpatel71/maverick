import { useEffect, useState } from "react";
import { api } from "../api";
import Dialog from "./Dialog";

interface Share { id: string; email: string; access: string }

interface Props {
  resourceType: "agent" | "rag";
  resourceId: string;
  resourceName: string;
  onClose: () => void;
}

export default function ShareModal({ resourceType, resourceId, resourceName, onClose }: Props) {
  const [shares, setShares] = useState<Share[]>([]);
  const [email, setEmail] = useState("");
  const [access, setAccess] = useState<"read" | "write">("read");
  const [adding, setAdding] = useState(false);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.listShares(resourceType, resourceId).then(setShares).catch(() => {});
  }, [resourceType, resourceId]);

  async function handleAdd() {
    if (!email.trim()) return;
    setErr("");
    setAdding(true);
    try {
      const share = await api.createShare(resourceType, resourceId, email.trim(), access);
      setShares(s => [...s, share]);
      setEmail("");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed to share");
    } finally {
      setAdding(false);
    }
  }

  async function handleRevoke(shareId: string) {
    setRevoking(shareId);
    try {
      await api.revokeShare(resourceType, resourceId, shareId);
      setShares(s => s.filter(x => x.id !== shareId));
    } finally {
      setRevoking(null);
    }
  }

  return (
    <Dialog
      title={`Share ${resourceType === "agent" ? "Agent" : "RAG"}`}
      subtitle={resourceName}
      size="md"
      onClose={onClose}
    >
      {/* Add form */}
      <div className="space-y-4">
        <div>
          <p className="text-xs font-medium text-slate-700 mb-2">Invite by email</p>
          <div className="flex gap-2">
            <input
              type="email"
              placeholder="user@company.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleAdd()}
              className="flex-1 px-3 py-2 text-sm rounded-lg border border-border bg-bg focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent min-w-0"
            />
            <select
              value={access}
              onChange={e => setAccess(e.target.value as "read" | "write")}
              className="px-2 py-2 text-xs rounded-lg border border-border bg-bg focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
            >
              <option value="read">Read</option>
              <option value="write">Write</option>
            </select>
            <button
              onClick={handleAdd}
              disabled={adding || !email.trim()}
              className="px-3 py-2 bg-accent text-white text-xs font-medium rounded-lg hover:bg-accent/90 disabled:opacity-50 transition-all flex-shrink-0"
            >
              {adding ? "…" : "Add"}
            </button>
          </div>
          {err && <p className="text-xs text-red-500 mt-1.5">{err}</p>}
          <div className="mt-2 flex gap-3 text-[11px] text-muted">
            <span><span className="font-medium text-slate-600">Read</span> — chat &amp; stream only</span>
            <span><span className="font-medium text-slate-600">Write</span> — full edit access</span>
          </div>
        </div>

        {/* Existing shares */}
        <div className="max-h-64 overflow-y-auto">
          {shares.length === 0 ? (
            <p className="text-xs text-muted text-center py-4">Not shared with anyone yet</p>
          ) : (
            <div className="space-y-2">
              {shares.map(s => (
                <div key={s.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                  <div>
                    <p className="text-xs font-medium text-slate-800">{s.email}</p>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${
                      s.access === "write"
                        ? "bg-violet-50 text-violet-600 border-violet-200"
                        : "bg-slate-50 text-slate-500 border-slate-200"
                    }`}>
                      {s.access}
                    </span>
                  </div>
                  <button
                    onClick={() => handleRevoke(s.id)}
                    disabled={revoking === s.id}
                    className="text-xs text-red-400 hover:text-red-600 disabled:opacity-40 font-medium"
                  >
                    {revoking === s.id ? "…" : "Revoke"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Dialog>
  );
}
