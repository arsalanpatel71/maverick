export interface SkillCatalogEntry {
  name: string;
  description: string;
  github_url: string;
  imported: boolean;
  skill_id: string | null;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  content: string;
  source: "builtin" | "github" | "custom";
  github_url: string | null;
  owner_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PageMeta {
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PagedResponse<T> {
  items: T[];
  meta: PageMeta;
}

export interface RAGConfig {
  rag_ids: string[];
  top_k: number;
  retrieval_type: string;
  lambda_param: number;
  score_threshold: number;
  time_decay_factor: number;
}

export interface ManagedAgent {
  id: string;
  name: string;
  usage_description: string;
}

export interface ResponseSchema {
  name: string;
  json_schema: Record<string, unknown>;
  description: string | null;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  goal: string;
  instructions: string;
  model: string;
  provider: string;
  memory_enabled: boolean;
  memory_max_messages: number | null;
  rag_config: RAGConfig | null;
  managed_agents: ManagedAgent[];
  response_schema: ResponseSchema | null;
  skill_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface RAGItem {
  id: string;
  name: string;
  description: string | null;
  vector_store: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  created_at: string;
  updated_at: string;
}

export interface LLMModelEntry {
  id: string;
  description: string;
}

export interface ProviderModels {
  provider: string;
  models: LLMModelEntry[];
}

export interface TraceEvent {
  type: string;
  data: Record<string, unknown>;
  ts: string;
}

export type CapsuleFormat =
  | "text" | "code" | "json" | "markdown" | "data" | "image"
  | "csv" | "xlsx" | "pdf" | "docx" | "pptx";

export interface Capsule {
  capsule_id: string;
  agent_id: string;
  session_id: string | null;
  user_id: string | null;
  format_type: CapsuleFormat;
  name: string;
  description: string;
  data: string | null;
  metadata: {
    language?: string;
    file_url?: string;
    file_name?: string;
    file_type?: string;
    s3_key?: string;
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
}

export interface WsMessage {
  event: "trace" | "response" | "error" | "done";
  type?: string;
  data?: Record<string, unknown>;
  ts?: string;
  content?: string;
  structured_output?: Record<string, unknown> | null;
  usage?: { input_tokens: number; output_tokens: number } | null;
  trace_id?: string;
  capsule_ids?: string[];
  detail?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  traceId?: string;
  structuredOutput?: Record<string, unknown> | null;
  capsules?: Capsule[];
}

export interface RAGChunk {
  id: string;
  rag_id: string;
  name: string;
  data: string;
  source: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface RAGChunkResult extends RAGChunk {
  score: number;
}

export interface RAGChatResponse {
  query: string;
  retrieval_type: string;
  top_k: number;
  total_found: number;
  chunks: RAGChunkResult[];
}
