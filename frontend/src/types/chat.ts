export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  /** 本轮后端返回的快照，用于展示协作 / 成果（可选） */
  runtime_session?: RuntimeSessionSnapshot;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  reply: string;
  session_id: string;
  timestamp: string;
  runtime_session?: RuntimeSessionSnapshot;
}

export interface SessionResponse {
  session_id: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export interface RuntimeSessionSnapshot {
  session_id: string;
  user_input: string;
  planner_result: Record<string, unknown> | null;
  workflow_result: Record<string, unknown> | null;
  tool_calls: Array<Record<string, unknown>>;
  model_calls: Array<Record<string, unknown>>;
  workflow_trace: Array<Record<string, unknown>>;
  collaboration_trace?: Array<Record<string, unknown>>;
  deliverables?: Array<Record<string, unknown>>;
  final_output: string | null;
  errors: string[];
}

export interface TranscriptEntryResponse {
  type: string;
  user_input: string;
  final_output: string | null;
  success: boolean;
  timestamp: string;
  runtime_session: RuntimeSessionSnapshot;
}

export interface DiffItemResponse {
  field: string;
  base: unknown;
  compare: unknown;
  changed: boolean;
}

export interface TranscriptDiffResponse {
  session_id: string;
  base_index: number;
  compare_index: number;
  base_timestamp: string;
  compare_timestamp: string;
  changed: boolean;
  items: DiffItemResponse[];
}

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
  };
}
