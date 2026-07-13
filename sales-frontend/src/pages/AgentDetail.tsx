import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, BASE } from "../api";
import type { Agent, Capsule, ChatMessage, ProviderModels, RAGItem, Skill, TraceEvent } from "../types";
import CapsuleCard from "../components/capsule/CapsuleCard";
import { formFromAgent, emptyForm, formsEqual } from "../components/agent/types";
import type { FormState } from "../components/agent/types";
import AgentForm from "../components/agent/AgentForm";
import AttachmentsPanel from "../components/agent/AttachmentsPanel";
import TraceEventCard from "../components/agent/TraceEventCard";
import CopyButton from "../components/agent/CopyButton";
import JsonBlock, { tryParseJson } from "../components/agent/JsonBlock";

export default function AgentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isNew = id === "new";

  const [agent, setAgent] = useState<Agent | null>(null);
  const [providers, setProviders] = useState<ProviderModels[]>([]);
  const [rags, setRags] = useState<RAGItem[]>([]);
  const [allAgents, setAllAgents] = useState<Agent[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(!isNew);

  const [form, setForm] = useState<FormState | null>(null);
  const [savedForm, setSavedForm] = useState<FormState | null>(null);

  const [myAccess, setMyAccess] = useState<"owner" | "write" | "read" | "none">("owner");
  const readOnly = myAccess === "read";

  const [formSaving, setFormSaving] = useState(false);
  const [formJustSaved, setFormJustSaved] = useState(false);
  const [formSaveError, setFormSaveError] = useState<string | null>(null);
  const doSaveRef = useRef<(() => void) | null>(null);

  const isDirty = form && savedForm && !isNew ? !formsEqual(form, savedForm) : false;

  function updateForm(updater: ((prev: FormState) => FormState) | FormState) {
    setForm((prev) => {
      if (prev === null) return prev;
      return typeof updater === "function" ? updater(prev) : updater;
    });
  }

  const [tab, setTab] = useState<"chat" | "activity">("chat");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());

  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [latestTraceId, setLatestTraceId] = useState<string | null>(null);
  const [capsuleMap, setCapsuleMap] = useState<Record<string, Capsule>>({});

  const chatEndRef = useRef<HTMLDivElement>(null);
  const activityEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isNew) {
      Promise.all([api.listProviders(), api.listRags(), api.listAgents(), api.listSkills()])
        .then(([p, r, ag, sk]) => {
          setProviders(p); setRags(r.items); setAllAgents(ag.items); setSkills(sk.items);
          const f = emptyForm(p);
          setForm(f); setSavedForm(f);
        })
        .catch(() => {
          const f = emptyForm([]);
          setForm(f); setSavedForm(f);
        });
      return;
    }
    if (!id) return;
    Promise.all([api.getAgent(id), api.listProviders(), api.listRags(), api.listAgents(), api.myAgentAccess(id), api.listSkills()])
      .then(([a, p, r, ag, acc, sk]) => {
        setAgent(a); setProviders(p); setRags(r.items); setAllAgents(ag.items); setSkills(sk.items);
        const f = formFromAgent(a);
        setForm(f); setSavedForm(f);
        setMyAccess((acc as { access: string }).access as typeof myAccess);
      })
      .catch(() => setAgent(null))
      .finally(() => setLoading(false));
  }, [id, isNew]);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => { activityEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [events]);

  useEffect(() => {
    const toFetch = events.filter(
      (e) => e.type === "capsule_created" && e.data.capsule_id && !capsuleMap[e.data.capsule_id as string]
    );
    if (toFetch.length === 0) return;
    Promise.all(
      toFetch.map((e) => api.getCapsule(e.data.capsule_id as string).catch(() => null))
    ).then((caps) => {
      const updates: Record<string, Capsule> = {};
      caps.forEach((cap, i) => {
        if (cap) updates[toFetch[i].data.capsule_id as string] = cap;
      });
      if (Object.keys(updates).length > 0) setCapsuleMap((prev) => ({ ...prev, ...updates }));
    });
  }, [events]);

  async function sendMessage() {
    if (!input.trim() || sending || !id || isNew) return;

    const userMsg = input.trim();
    setInput(""); setSending(true);
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setTab("activity");

    try {
      const res = await fetch(`${BASE}/agents/message/stream`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_id: id, message: userMsg, session_id: sessionId }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`${res.status} ${res.statusText}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          try {
            const msg = JSON.parse(part.slice(6));
            if (msg.event === "trace" && msg.type && msg.data !== undefined) {
              setEvents((prev) => [...prev, { type: msg.type!, data: msg.data ?? {}, ts: msg.ts ?? new Date().toISOString() }]);
            }
            if (msg.event === "response" && msg.content) {
              // Add the message immediately so it appears when the chat tab opens
              setMessages((prev) => [
                ...prev,
                { role: "assistant", content: msg.content!, traceId: msg.trace_id },
              ]);
              if (msg.trace_id) setLatestTraceId(msg.trace_id);

              // Fetch capsules and patch them onto the message once ready
              const capsuleIds: string[] = msg.capsule_ids ?? [];
              if (capsuleIds.length > 0) {
                const traceId = msg.trace_id;
                Promise.all(capsuleIds.map((cid) => api.getCapsule(cid).catch(() => null)))
                  .then((caps) => {
                    const valid = caps.filter((c): c is Capsule => c !== null);
                    if (valid.length === 0) return;
                    setMessages((prev) => {
                      const next = [...prev];
                      for (let i = next.length - 1; i >= 0; i--) {
                        if (next[i].role === "assistant" && next[i].traceId === traceId) {
                          next[i] = { ...next[i], capsules: valid };
                          break;
                        }
                      }
                      return next;
                    });
                  });
              }
            }
            if (msg.event === "done") { setSending(false); setTab("chat"); }
            if (msg.event === "error") {
              setEvents((prev) => [...prev, { type: "error", data: { detail: msg.detail }, ts: new Date().toISOString() }]);
              setSending(false);
            }
          } catch {}
        }
      }
    } catch (e) {
      setEvents((prev) => [...prev, { type: "error", data: { detail: e instanceof Error ? e.message : "Request failed" }, ts: new Date().toISOString() }]);
      setSending(false);
    }
  }

  if (loading || (!isNew && !form)) {
    return (
      <div className="h-full flex items-center justify-center text-muted">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading agent…</span>
        </div>
      </div>
    );
  }

  if (!isNew && !agent) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted text-sm mb-4">Agent not found.</p>
          <button onClick={() => navigate("/agents")} className="text-accent text-sm hover:underline">← Back to agents</button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Top bar */}
      <div className="border-b border-border px-6 py-3.5 flex items-center gap-3 flex-shrink-0 bg-surface">
        <button onClick={() => navigate("/agents")} className="text-muted hover:text-slate-700 transition-colors text-sm">← Agents</button>
        <span className="text-border">|</span>
        <span className="text-slate-900 text-sm font-medium truncate">{isNew ? "New Agent" : (agent!.name || agent!.role)}</span>
        <div className="ml-auto flex items-center gap-3">
          {!isNew && agent && (
            <span className="flex items-center gap-2 type-caption">
              <span className="font-mono bg-bg border border-border px-2 py-0.5 rounded text-slate-500">{agent.id.slice(0, 8)}…</span>
              <span className="hidden sm:inline text-muted">{new Date(agent.created_at).toLocaleDateString()}</span>
            </span>
          )}
          {formJustSaved && <span className="text-xs text-emerald-600 font-medium">Saved</span>}
          {formSaveError && <span className="text-xs text-red-500 max-w-[150px] truncate" title={formSaveError}>{formSaveError}</span>}
          {readOnly ? (
            <span className="text-xs px-2.5 py-1.5 bg-amber-50 border border-amber-200 text-amber-700 rounded-lg font-medium">
              Read-only access
            </span>
          ) : (
            <button
              onClick={() => doSaveRef.current?.()}
              disabled={formSaving || (!isNew && !isDirty)}
              className="px-3 py-1.5 bg-accent hover:bg-accent-muted disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-xs font-medium transition-colors"
            >
              {formSaving ? (isNew ? "Creating…" : "Saving…") : (isNew ? "Create agent" : "Save changes")}
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: form — 35% */}
        <div className={`${isNew ? "flex-1" : "w-[35%]"} border-r border-border overflow-y-auto scrollbar-thin p-5 flex-shrink-0`}>
          {form && savedForm && (
            <AgentForm
              form={form}
              onFormChange={setForm}
              savedForm={savedForm}
              onSavedFormChange={setSavedForm}
              agent={agent}
              providers={providers}
              isNew={isNew}
              readOnly={readOnly}
              onCreated={(a) => { setAgent(a); const f = formFromAgent(a); setForm(f); setSavedForm(f); }}
              onSaved={(a) => { setAgent(a); }}
              onSavingChange={setFormSaving}
              onJustSavedChange={setFormJustSaved}
              onSaveErrorChange={setFormSaveError}
              doSaveRef={doSaveRef}
            />
          )}
        </div>

        {/* Middle: attachments — 27% */}
        {!isNew && form && (
          <div className="w-[27%] border-r border-border flex-shrink-0 flex flex-col overflow-hidden">
            <AttachmentsPanel
              form={form}
              setForm={updateForm}
              rags={rags}
              allAgents={allAgents}
              skills={skills}
              agentId={agent?.id ?? null}
              readOnly={readOnly}
            />
          </div>
        )}

        {/* Right: chat + activity */}
        {!isNew && (
          <div className="flex-1 flex flex-col overflow-hidden min-w-0">
            <div className="flex border-b border-border flex-shrink-0 bg-surface">
              {(["chat", "activity"] as const).map((t) => (
                <button
                  key={t} onClick={() => setTab(t)}
                  className={`flex-1 py-3 text-xs font-medium uppercase tracking-wider transition-colors relative ${tab === t ? "text-accent" : "text-muted hover:text-slate-600"}`}
                >
                  {t === "chat" ? "💬 Chat" : "⚡ Activity"}
                  {tab === t && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />}
                  {t === "activity" && sending && <span className="ml-1.5 w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block animate-pulse" />}
                </button>
              ))}
            </div>

            {tab === "chat" && (
              <div className="flex flex-col flex-1 overflow-hidden">
                <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-3">
                  {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-center gap-3 py-12">
                      <div className="text-3xl">💬</div>
                      <p className="text-muted text-xs leading-relaxed max-w-[200px]">
                        Send a message to start chatting with <strong className="text-slate-600">{agent!.name}</strong>.
                      </p>
                    </div>
                  )}
                  {messages.map((msg, i) => {
                    const jsonData = msg.role === "assistant" ? tryParseJson(msg.content) : null;
                    return (
                      <div key={i} className={`flex flex-col group ${msg.role === "user" ? "items-end" : "items-start"}`}>
                        {jsonData ? (
                          <JsonBlock raw={msg.content} />
                        ) : (
                          <>
                            <div className={`rounded-2xl px-3.5 py-2.5 text-sm max-w-[85%] leading-relaxed ${
                              msg.role === "user"
                                ? "bg-accent text-white rounded-br-sm"
                                : "bg-surface border border-border text-slate-700 rounded-bl-sm prose prose-sm prose-slate max-w-none"
                            }`}>
                              {msg.role === "assistant" ? (
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm]}
                                  components={{
                                    p: ({ children }) => <p className="mb-1.5 last:mb-0">{children}</p>,
                                    ul: ({ children }) => <ul className="list-disc pl-4 mb-1.5 space-y-0.5">{children}</ul>,
                                    ol: ({ children }) => <ol className="list-decimal pl-4 mb-1.5 space-y-0.5">{children}</ol>,
                                    li: ({ children }) => <li>{children}</li>,
                                    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                                    em: ({ children }) => <em>{children}</em>,
                                    code: ({ children, className }) =>
                                      className ? (
                                        <code className="block bg-slate-100 rounded px-2 py-1 text-xs font-mono overflow-x-auto">{children}</code>
                                      ) : (
                                        <code className="bg-slate-100 rounded px-1 text-xs font-mono">{children}</code>
                                      ),
                                    pre: ({ children }) => <pre className="bg-slate-100 rounded p-2 overflow-x-auto mb-1.5">{children}</pre>,
                                    a: ({ href, children }) => (
                                      <a href={href} target="_blank" rel="noopener noreferrer" className="underline text-accent">{children}</a>
                                    ),
                                    h1: ({ children }) => <h1 className="font-bold text-base mb-1">{children}</h1>,
                                    h2: ({ children }) => <h2 className="font-bold mb-1">{children}</h2>,
                                    h3: ({ children }) => <h3 className="font-semibold mb-1">{children}</h3>,
                                    blockquote: ({ children }) => <blockquote className="border-l-2 border-slate-300 pl-3 opacity-70">{children}</blockquote>,
                                    hr: () => <hr className="my-2 border-slate-200" />,
                                  }}
                                >
                                  {msg.content}
                                </ReactMarkdown>
                              ) : (
                                msg.content
                              )}
                            </div>
                            <CopyButton text={msg.content} />
                            {msg.capsules && msg.capsules.length > 0 && (
                              <div className="w-full max-w-[85%] mt-1.5 space-y-1.5">
                                {msg.capsules.map((cap) => (
                                  <CapsuleCard key={cap.capsule_id} capsule={cap} />
                                ))}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    );
                  })}
                  {sending && (
                    <div className="flex justify-start">
                      <div className="bg-surface border border-border rounded-2xl rounded-bl-sm px-3.5 py-2.5">
                        <div className="flex gap-1 items-center h-4">
                          {[0, 1, 2].map((i) => <div key={i} className="w-1.5 h-1.5 rounded-full bg-muted animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />)}
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>
                <div className="border-t border-border p-3 flex-shrink-0 bg-surface">
                  <div className="flex gap-2">
                    <input
                      value={input} onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                      placeholder="Message…" disabled={sending}
                      className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-sm text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light disabled:opacity-50 transition-colors"
                    />
                    <button onClick={sendMessage} disabled={sending || !input.trim()}
                      className="px-3 py-2 bg-accent hover:bg-accent-muted disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors">
                      {sending ? "…" : "→"}
                    </button>
                  </div>
                  {agent?.memory_enabled && <p className="type-caption mt-1.5 text-center">Memory on · session {sessionId.slice(0, 8)}…</p>}
                </div>
              </div>
            )}

            {tab === "activity" && (
              <div className="flex flex-col flex-1 overflow-hidden">
                <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-2">
                  {events.length === 0 && !sending && (
                    <div className="flex flex-col items-center justify-center h-full text-center gap-3 py-12">
                      <div className="text-3xl">⚡</div>
                      <p className="text-muted text-xs max-w-[200px]">Activity will stream here when you send a message.</p>
                    </div>
                  )}
                  {events.map((ev, i) => (
                    <TraceEventCard
                      key={i}
                      event={ev}
                      capsule={ev.data.capsule_id ? capsuleMap[ev.data.capsule_id as string] : undefined}
                    />
                  ))}
                  {sending && (
                    <div className="flex items-center gap-2 text-xs text-muted px-1 py-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      Processing…
                    </div>
                  )}
                  <div ref={activityEndRef} />
                </div>
                {latestTraceId && (
                  <div className="border-t border-border p-3 flex-shrink-0">
                    <p className="type-caption">Last trace: <span className="font-mono text-accent">{latestTraceId.slice(0, 16)}…</span></p>
                  </div>
                )}
                {events.length > 0 && (
                  <div className="border-t border-border p-3 flex-shrink-0">
                    <button onClick={() => setEvents([])} className="text-xs text-muted hover:text-slate-600 transition-colors">Clear activity</button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
