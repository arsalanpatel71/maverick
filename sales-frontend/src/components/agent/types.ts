import type { Agent, ManagedAgent, ProviderModels } from "../../types";

export type { ManagedAgent };

export interface RAGSettings {
  top_k: number; retrieval_type: string; lambda_param: number; score_threshold: number; time_decay_factor: number;
}

export interface FormState {
  name: string; role: string; goal: string; instructions: string;
  provider: string; model: string;
  memory_enabled: boolean; memory_max_messages: number;
  rag_id: string; rag_settings: RAGSettings;
  managed_agents: ManagedAgent[];
  schema_enabled: boolean;
  schema_name: string;
  schema_desc: string;
  schema_json: string;
  skill_ids: string[];
}

export const DEFAULT_RAG_SETTINGS: RAGSettings = { top_k: 10, retrieval_type: "basic", lambda_param: 0.6, score_threshold: 0, time_decay_factor: 0.7 };

export function formFromAgent(agent: Agent): FormState {
  const rc = agent.rag_config;
  const rs = agent.response_schema;
  return {
    name: agent.name, role: agent.role, goal: agent.goal, instructions: agent.instructions,
    provider: agent.provider, model: agent.model,
    memory_enabled: agent.memory_enabled, memory_max_messages: agent.memory_max_messages ?? 10,
    rag_id: rc?.rag_ids?.[0] ?? "",
    rag_settings: rc ? { top_k: rc.top_k, retrieval_type: rc.retrieval_type, lambda_param: rc.lambda_param, score_threshold: rc.score_threshold, time_decay_factor: rc.time_decay_factor } : { ...DEFAULT_RAG_SETTINGS },
    managed_agents: agent.managed_agents ?? [],
    skill_ids: agent.skill_ids ?? [],
    schema_enabled: rs != null,
    schema_name: rs?.name ?? "",
    schema_desc: rs?.description ?? "",
    schema_json: rs ? JSON.stringify(rs.json_schema, null, 2) : "",
  };
}

export function emptyForm(providers: ProviderModels[]): FormState {
  const first = providers[0];
  return { name: "", role: "", goal: "", instructions: "", provider: first?.provider ?? "google", model: first?.models?.[0]?.id ?? "", memory_enabled: false, memory_max_messages: 10, rag_id: "", rag_settings: { ...DEFAULT_RAG_SETTINGS }, managed_agents: [], skill_ids: [], schema_enabled: false, schema_name: "", schema_desc: "", schema_json: "" };
}

export function formsEqual(a: FormState, b: FormState) { return JSON.stringify(a) === JSON.stringify(b); }

export const inputCls = "w-full bg-surface border border-border rounded-lg px-3 py-2.5 text-sm text-slate-800 placeholder-muted focus:outline-none focus:border-accent-light focus:ring-2 focus:ring-accent-light/20 transition-colors";
export const selectCls = `${inputCls} cursor-pointer`;
