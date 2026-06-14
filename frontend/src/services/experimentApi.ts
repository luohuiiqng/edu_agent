import type { ErrorResponse } from "../types/chat";
import type {
  ExperimentListResponse,
  ExperimentPairRunResponse,
  ExperimentRunAllResponse,
  ExperimentRunResponse,
} from "../types/experiment";

const API_BASE_URL = "";

export async function fetchExperiments(): Promise<ExperimentListResponse> {
  return requestJson<ExperimentListResponse>("/agent_api/experiments");
}

export async function runExperiment(
  experimentId: string,
  options?: { includeControl?: boolean },
): Promise<ExperimentRunResponse | ExperimentPairRunResponse> {
  const query = new URLSearchParams({
    include_control: String(options?.includeControl ?? true),
  });
  return requestJson<ExperimentRunResponse | ExperimentPairRunResponse>(
    `/agent_api/experiments/${experimentId}/run?${query.toString()}`,
    { method: "POST" },
  );
}

export async function runAllExperiments(options?: {
  skipFfmpeg?: boolean;
  includeControl?: boolean;
  compact?: boolean;
}): Promise<ExperimentRunAllResponse> {
  const query = new URLSearchParams({
    skip_ffmpeg: String(options?.skipFfmpeg ?? false),
    include_control: String(options?.includeControl ?? true),
    compact: String(options?.compact ?? true),
  });
  return requestJson<ExperimentRunAllResponse>(
    `/agent_api/experiments/run-all?${query.toString()}`,
    { method: "POST" },
  );
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as ErrorResponse | null;
    const message = errorBody?.error?.message ?? "请求失败，请稍后重试";
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function isExperimentPairResult(
  result: ExperimentRunResponse | ExperimentPairRunResponse,
): result is ExperimentPairRunResponse {
  return "main" in result;
}
