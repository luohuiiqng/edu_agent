export interface ExperimentSummary {
  id: string;
  title: string;
  message: string;
  agent_profile: string;
  has_control: boolean;
}

export interface ExperimentListResponse {
  experiments: ExperimentSummary[];
}

export interface EvalCheckResponse {
  rule: string;
  passed: boolean;
  message: string;
}

export interface EvalResultResponse {
  passed: boolean;
  checks: EvalCheckResponse[];
}

export interface ExperimentRunResponse {
  experiment_id: string;
  title: string;
  message: string;
  passed: boolean;
  agent_success: boolean;
  eval: EvalResultResponse;
  runtime_session?: Record<string, unknown> | null;
}

export interface ExperimentPairRunResponse {
  passed: boolean;
  main: ExperimentRunResponse;
  control?: ExperimentRunResponse | null;
  diff?: {
    changed: boolean;
    items?: Array<Record<string, unknown>>;
  } | null;
}

export interface ExperimentRunAllResponse {
  passed: boolean;
  total: number;
  passed_count: number;
  skip_ffmpeg: boolean;
  ffmpeg_available: boolean;
  results: Array<ExperimentRunResponse | ExperimentPairRunResponse>;
}
