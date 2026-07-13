import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import Dialog from "../components/Dialog";
import Input from "../components/Input";
import Select from "../components/Select";

interface UserRow {
  id: string; email: string; name: string; role: string;
  credits_limit: number; credits_used: number; credits_period: string; is_active: boolean; created_at: string;
}

const PERIOD_OPTIONS = [
  { value: "daily",   label: "Daily" },
  { value: "weekly",  label: "Weekly" },
  { value: "monthly", label: "Monthly" },
];

const ROLE_STYLE: Record<string, string> = {
  super_admin: "bg-violet-50 text-violet-700 border-violet-200",
  admin:       "bg-blue-50 text-blue-600 border-blue-200",
  member:      "bg-slate-50 text-slate-600 border-slate-200",
};

const PERIOD_SHORT: Record<string, string> = { daily: "day", weekly: "week", monthly: "month" };

function UsageCell({ used, period }: { used: number; period: string }) {
  return (
    <div>
      <span className="font-mono text-slate-800 text-xs font-semibold">${used.toFixed(4)}</span>
      <span className="text-muted text-xs ml-1">this {PERIOD_SHORT[period] ?? period}</span>
    </div>
  );
}

function EditCreditsModal({ user, onClose, onSave }: {
  user: UserRow; onClose: () => void; onSave: (id: string, limit: number, period: string) => Promise<void>;
}) {
  const [val, setVal] = useState(String(user.credits_limit));
  const [period, setPeriod] = useState(user.credits_period || "monthly");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  async function save() {
    const n = parseFloat(val);
    if (isNaN(n) || n < 0) { setErr("Must be a positive number"); return; }
    setSaving(true);
    try { await onSave(user.id, n, period); onClose(); }
    catch (e: unknown) { setErr(e instanceof Error ? e.message : "Failed"); setSaving(false); }
  }

  const footer = (
    <>
      <button onClick={onClose} className="flex-1 py-2 rounded-lg border border-border text-sm text-muted hover:bg-bg transition-all">Cancel</button>
      <button onClick={save} disabled={saving} className="flex-1 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-all">
        {saving ? "Saving…" : "Save"}
      </button>
    </>
  );

  return (
    <Dialog title={`Edit Credits — ${user.name}`} subtitle={user.email} size="sm" onClose={onClose} footer={footer}>
      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">Limit (USD)</label>
            <Input type="number" min="0" step="1" value={val} onChange={e => setVal(e.target.value)} autoFocus />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">Resets</label>
            <Select value={period} onChange={e => setPeriod(e.target.value)}>
              {PERIOD_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </Select>
          </div>
        </div>
        <p className="text-xs text-muted">Usage resets to $0 at the start of each {period === "daily" ? "day" : period === "weekly" ? "week" : "month"}. Saving will reset current usage immediately.</p>
        {err && <p className="text-xs text-red-500">{err}</p>}
      </div>
    </Dialog>
  );
}

function AddUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ email: "", name: "", password: "", credits_limit: "10", credits_period: "monthly", role: "member" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  function set(k: string, v: string) { setForm(f => ({ ...f, [k]: v })); }

  async function save() {
    if (!form.email || !form.name || !form.password) { setErr("All fields required"); return; }
    setSaving(true);
    try {
      await api.createUser({ ...form, credits_limit: parseFloat(form.credits_limit) || 10 });
      onCreated(); onClose();
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : "Failed"); setSaving(false); }
  }

  const footer = (
    <>
      <button onClick={onClose} className="flex-1 py-2 rounded-lg border border-border text-sm text-muted hover:bg-bg transition-all">Cancel</button>
      <button onClick={save} disabled={saving} className="flex-1 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-all">
        {saving ? "Creating…" : "Create"}
      </button>
    </>
  );

  return (
    <Dialog title="Add User" size="sm" onClose={onClose} footer={footer}>
      <div className="space-y-3">
        {[["Name", "name", "text", "Full name"], ["Email", "email", "email", "user@company.com"], ["Password", "password", "password", "••••••••"]].map(([label, key, type, ph]) => (
          <div key={key}>
            <label className="block text-xs font-medium text-slate-700 mb-1">{label}</label>
            <Input type={type} placeholder={ph} value={form[key as keyof typeof form]} onChange={e => set(key, e.target.value)} />
          </div>
        ))}
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Limit ($)</label>
            <Input type="number" min="0" value={form.credits_limit} onChange={e => set("credits_limit", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Resets</label>
            <Select value={form.credits_period} onChange={e => set("credits_period", e.target.value)}>
              {PERIOD_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </Select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Role</label>
            <Select value={form.role} onChange={e => set("role", e.target.value)}>
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </Select>
          </div>
        </div>
        {err && <p className="text-xs text-red-500">{err}</p>}
      </div>
    </Dialog>
  );
}

export default function Admin() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [editUser, setEditUser] = useState<UserRow | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);

  async function load() {
    try { setUsers((await api.listUsers()) as unknown as UserRow[]); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  async function handleUpdateCredits(id: string, limit: number, period: string) {
    await api.updateUserCredits(id, limit, period);
    setUsers(u => u.map(x => x.id === id ? { ...x, credits_limit: limit, credits_period: period, credits_used: 0 } : x));
  }

  async function handleRemove(user: UserRow) {
    if (!confirm(`Deactivate ${user.name} (${user.email})? They will lose access.`)) return;
    setRemoving(user.id);
    try {
      await api.deactivateUser(user.id);
      setUsers(u => u.map(x => x.id === user.id ? { ...x, is_active: false } : x));
    } finally { setRemoving(null); }
  }

  return (
    <div className="h-full overflow-y-auto bg-bg">
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">User Management</h1>
            <p className="text-sm text-muted mt-0.5">Manage org members and credit limits</p>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-accent/90 transition-all"
          >
            <svg viewBox="0 0 16 16" fill="none" className="w-4 h-4">
              <path d="M8 1.5v13M1.5 8h13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Add User
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {[
            { label: "Total users", value: users.length },
            { label: "Active",      value: users.filter(u => u.is_active).length },
          ].map(s => (
            <div key={s.label} className="bg-surface border border-border rounded-xl px-5 py-4">
              <p className="text-xs font-medium text-muted">{s.label}</p>
              <p className="text-2xl font-bold text-slate-900 mt-0.5">{s.value}</p>
            </div>
          ))}
        </div>

        {/* Users table */}
        <div className="bg-surface border border-border rounded-xl overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-32 text-muted text-sm">Loading…</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-5 py-3 text-xs font-medium text-muted">User</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted">Role</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted w-44">Usage</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted">Status</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} className={`border-b border-border last:border-0 transition-colors ${u.is_active ? "hover:bg-bg/50" : "opacity-40"}`}>
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-slate-800">{u.name}</p>
                      <p className="text-xs text-muted">{u.email}</p>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${ROLE_STYLE[u.role] ?? ROLE_STYLE.member}`}>
                        {u.role.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 w-44">
                      <UsageCell used={u.credits_used} period={u.credits_period || "monthly"} />
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                        u.is_active ? "bg-emerald-50 text-emerald-600 border-emerald-200" : "bg-slate-50 text-slate-400 border-slate-200"
                      }`}>
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      {u.id !== me?.id && u.is_active && (
                        <div className="flex items-center gap-2 justify-end">
                          <button
                            onClick={() => setEditUser(u)}
                            className="text-xs text-accent hover:underline font-medium"
                          >
                            Edit credits
                          </button>
                          <span className="text-border">·</span>
                          <button
                            onClick={() => handleRemove(u)}
                            disabled={removing === u.id}
                            className="text-xs text-red-500 hover:underline font-medium disabled:opacity-40"
                          >
                            {removing === u.id ? "Removing…" : "Remove"}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {editUser && (
        <EditCreditsModal user={editUser} onClose={() => setEditUser(null)} onSave={handleUpdateCredits} />
      )}
      {showAdd && (
        <AddUserModal onClose={() => setShowAdd(false)} onCreated={load} />
      )}
    </div>
  );
}
