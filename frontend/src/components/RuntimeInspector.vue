<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";

import { fetchSessions, fetchTranscript, fetchTranscriptDiff } from "../services/chatApi";
import type { SessionResponse, TranscriptDiffResponse, TranscriptEntryResponse } from "../types/chat";

const props = defineProps<{
  activeSessionId?: string;
  refreshKey: number;
}>();

const emit = defineEmits<{
  sessionSelected: [sessionId: string];
}>();

const sessions = ref<SessionResponse[]>([]);
const transcript = ref<TranscriptEntryResponse[]>([]);
const sessionsLoading = ref(false);
const transcriptLoading = ref(false);
const sessionsError = ref("");
const transcriptError = ref("");
const selectedSessionId = ref<string>("");
const expandedEntryId = ref<string>("");
const expandedTraceIds = ref<string[]>([]);
const transcriptListRef = ref<HTMLElement | null>(null);
const transcriptCardRefs = ref<Record<string, HTMLElement | null>>({});
const traceStatusFilter = ref<"all" | "success" | "failure">("all");
const traceActionFilter = ref<"all" | "planner" | "tool" | "model" | "workflow">("all");
const traceSearch = ref("");
const transcriptStatusFilter = ref<"all" | "success" | "failure">("all");
const transcriptSearch = ref("");
const sessionSearch = ref("");
const diffBaseIndex = ref(0);
const diffCompareIndex = ref(1);
const diffResult = ref<TranscriptDiffResponse | null>(null);
const diffLoading = ref(false);
const diffError = ref("");

const diffChangedItems = computed(() =>
  (diffResult.value?.items ?? []).filter((item) => item.changed),
);

const selectedSession = computed(() =>
  sessions.value.find((session) => session.session_id === selectedSessionId.value),
);

const totalFailedTranscriptCount = computed(
  () => transcript.value.filter((entry) => !entry.success).length,
);

const sessionFailureCounts = computed(() => {
  const counts = new Map<string, number>();

  for (const entry of transcript.value) {
    if (!entry.success) {
      counts.set(entry.runtime_session.session_id, (counts.get(entry.runtime_session.session_id) ?? 0) + 1);
    }
  }

  return counts;
});

const filteredSessions = computed(() => {
  const searchValue = sessionSearch.value.trim().toLowerCase();
  if (!searchValue) {
    return sessions.value;
  }

  return sessions.value.filter((session) => {
    const haystack = [
      session.session_id,
      session.created_at,
      session.updated_at,
      JSON.stringify(session.metadata ?? {}),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(searchValue);
  });
});

const activeTranscriptEntry = computed(() => {
  if (transcript.value.length === 0) {
    return null;
  }

  if (expandedEntryId.value) {
    const matchedEntry = transcript.value.find((entry, index) => buildEntryId(entry, index) === expandedEntryId.value);
    if (matchedEntry) {
      return matchedEntry;
    }
  }

  return transcript.value[0] ?? null;
});

const latestRuntimeSession = computed(() => activeTranscriptEntry.value?.runtime_session ?? null);
const plannerResult = computed(() => latestRuntimeSession.value?.planner_result ?? null);
const plannerSteps = computed(() => {
  const steps = plannerResult.value?.steps;
  return Array.isArray(steps) ? steps : [];
});
const plannerContext = computed(() => {
  const context = plannerResult.value?.context;
  return context && typeof context === "object" ? context : null;
});
const workflowTrace = computed(() => latestRuntimeSession.value?.workflow_trace ?? []);
const failedWorkflowTraceCount = computed(
  () => workflowTrace.value.filter((trace) => !trace.success).length,
);
const filteredWorkflowTrace = computed(() =>
  workflowTrace.value.filter((trace) => {
    const matchesStatus =
      traceStatusFilter.value === "all"
        ? true
        : traceStatusFilter.value === "success"
          ? Boolean(trace.success)
          : !trace.success;

    const action = String(trace.action ?? "");
    const matchesAction =
      traceActionFilter.value === "all"
        ? true
        : traceActionFilter.value === "planner"
          ? String(trace.step_name ?? "") === "planner"
          : action === traceActionFilter.value;

    const searchValue = traceSearch.value.trim().toLowerCase();
    const haystack = [
      String(trace.step_name ?? ""),
      String(trace.action ?? ""),
      String(trace.input_summary ?? ""),
      String(trace.output_summary ?? ""),
    ]
      .join(" ")
      .toLowerCase();
    const matchesSearch = !searchValue || haystack.includes(searchValue);

    return matchesStatus && matchesAction && matchesSearch;
  }),
);

const selectedSessionStats = computed(() => {
  if (transcript.value.length === 0) {
    return [
      { label: "记录条数", value: "0" },
      { label: "工具调用", value: "0" },
      { label: "模型调用", value: "0" },
    ];
  }

  const toolCallCount = transcript.value.reduce(
    (count, entry) => count + entry.runtime_session.tool_calls.length,
    0,
  );
  const modelCallCount = transcript.value.reduce(
    (count, entry) => count + entry.runtime_session.model_calls.length,
    0,
  );

  return [
    { label: "记录条数", value: String(transcript.value.length) },
    { label: "工具调用", value: String(toolCallCount) },
    { label: "模型调用", value: String(modelCallCount) },
  ];
});

const sessionPanelStats = computed(() => [
  { label: "可见会话", value: String(filteredSessions.value.length) },
  { label: "失败轮次", value: String(totalFailedTranscriptCount.value) },
  { label: "已选会话", value: selectedSession.value ? selectedSession.value.session_id.slice(0, 8) : "-" },
]);

const filteredTranscript = computed(() =>
  transcript.value.filter((entry) => {
    const matchesStatus =
      transcriptStatusFilter.value === "all"
        ? true
        : transcriptStatusFilter.value === "success"
          ? entry.success
          : !entry.success;

    const searchValue = transcriptSearch.value.trim().toLowerCase();
    const haystack = [
      entry.type,
      entry.user_input,
      entry.final_output ?? "",
      entry.runtime_session.final_output ?? "",
    ]
      .join(" ")
      .toLowerCase();
    const matchesSearch = !searchValue || haystack.includes(searchValue);

    return matchesStatus && matchesSearch;
  }),
);

onMounted(async () => {
  await loadSessions();
});

watch(
  () => props.activeSessionId,
  async (sessionId) => {
    if (!sessionId) {
      return;
    }

    selectedSessionId.value = sessionId;
    await loadTranscript(sessionId);
  },
  { immediate: true },
);

watch(
  () => props.refreshKey,
  async () => {
    await loadSessions();
    if (selectedSessionId.value) {
      await loadTranscript(selectedSessionId.value);
    }
  },
);

async function loadSessions() {
  sessionsLoading.value = true;
  sessionsError.value = "";

  try {
    sessions.value = await fetchSessions();

    if (!selectedSessionId.value && sessions.value.length > 0) {
      const latestSessionId = sessions.value[0].session_id;
      selectedSessionId.value = latestSessionId;
      emit("sessionSelected", latestSessionId);
      await loadTranscript(latestSessionId);
    }
  } catch (error) {
    sessionsError.value = error instanceof Error ? error.message : "会话列表加载失败";
  } finally {
    sessionsLoading.value = false;
  }
}

async function loadTranscript(sessionId: string) {
  if (!sessionId) {
    transcript.value = [];
    diffResult.value = null;
    return;
  }

  transcriptLoading.value = true;
  transcriptError.value = "";
  diffResult.value = null;

  try {
    transcript.value = await fetchTranscript(sessionId);
    if (transcript.value.length > 0) {
      expandedEntryId.value = buildEntryId(transcript.value[0], 0);
      diffBaseIndex.value = 0;
      diffCompareIndex.value = transcript.value.length > 1 ? 1 : 0;
      await scrollExpandedEntryIntoView();
    } else {
      expandedEntryId.value = "";
    }
  } catch (error) {
    transcriptError.value = error instanceof Error ? error.message : "记录加载失败";
  } finally {
    transcriptLoading.value = false;
  }
}

function transcriptRoundLabel(index: number) {
  const entry = transcript.value[index];
  if (!entry) {
    return `轮次 ${index + 1}`;
  }
  const preview = entry.user_input.slice(0, 24);
  return `轮次 ${index + 1}: ${preview}${entry.user_input.length > 24 ? "…" : ""}`;
}

async function runTranscriptDiff() {
  if (!selectedSessionId.value) {
    return;
  }
  if (transcript.value.length < 2) {
    diffError.value = "至少需要 2 轮 transcript 才能对比";
    diffResult.value = null;
    return;
  }
  if (diffBaseIndex.value === diffCompareIndex.value) {
    diffError.value = "请选择不同的基准轮次与对比轮次";
    diffResult.value = null;
    return;
  }

  diffLoading.value = true;
  diffError.value = "";
  try {
    diffResult.value = await fetchTranscriptDiff(
      selectedSessionId.value,
      diffBaseIndex.value,
      diffCompareIndex.value,
    );
  } catch (error) {
    diffError.value = error instanceof Error ? error.message : "Diff 加载失败";
    diffResult.value = null;
  } finally {
    diffLoading.value = false;
  }
}

async function handleSelectSession(sessionId: string) {
  selectedSessionId.value = sessionId;
  emit("sessionSelected", sessionId);
  resetTraceFilters();
  await loadTranscript(sessionId);
}

async function refreshInspector() {
  await loadSessions();
  if (selectedSessionId.value) {
    await loadTranscript(selectedSessionId.value);
  }
}

async function toggleRuntime(entryId: string) {
  expandedEntryId.value = expandedEntryId.value === entryId ? "" : entryId;
  if (expandedEntryId.value) {
    await scrollExpandedEntryIntoView();
  }
}

function resetTraceFilters() {
  traceStatusFilter.value = "all";
  traceActionFilter.value = "all";
  traceSearch.value = "";
}

function resetTranscriptFilters() {
  transcriptStatusFilter.value = "all";
  transcriptSearch.value = "";
}

function resetSessionSearch() {
  sessionSearch.value = "";
}

function getPlannerAction(entry: TranscriptEntryResponse) {
  const action = entry.runtime_session.planner_result?.action;
  return typeof action === "string" && action ? action : "unknown";
}

function buildTraceId(trace: Record<string, unknown>, index: number) {
  return `${String(trace.step_name ?? "trace")}-${index}`;
}

function isTraceExpanded(trace: Record<string, unknown>, index: number) {
  return expandedTraceIds.value.includes(buildTraceId(trace, index));
}

function toggleTraceDetails(trace: Record<string, unknown>, index: number) {
  const traceId = buildTraceId(trace, index);
  expandedTraceIds.value = expandedTraceIds.value.includes(traceId)
    ? expandedTraceIds.value.filter((id) => id !== traceId)
    : [...expandedTraceIds.value, traceId];
}

function expandFailedTraces() {
  expandedTraceIds.value = filteredWorkflowTrace.value
    .map((trace, index) => ({ trace, index }))
    .filter(({ trace }) => !trace.success)
    .map(({ trace, index }) => buildTraceId(trace, index));
}

function expandAllTraces() {
  expandedTraceIds.value = filteredWorkflowTrace.value.map((trace, index) =>
    buildTraceId(trace, index),
  );
}

function collapseAllTraces() {
  expandedTraceIds.value = [];
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function buildEntryId(entry: TranscriptEntryResponse, index: number) {
  return [
    entry.runtime_session.session_id,
    entry.timestamp,
    entry.type,
    entry.user_input,
    entry.final_output ?? "",
  ].join("__");
}

function setTranscriptCardRef(entryId: string, element: Element | null) {
  transcriptCardRefs.value = {
    ...transcriptCardRefs.value,
    [entryId]: element instanceof HTMLElement ? element : null,
  };
}

async function scrollExpandedEntryIntoView() {
  await nextTick();

  if (!expandedEntryId.value) {
    return;
  }

  const container = transcriptListRef.value;
  const card = transcriptCardRefs.value[expandedEntryId.value];
  if (!container || !card) {
    return;
  }

  const containerRect = container.getBoundingClientRect();
  const cardRect = card.getBoundingClientRect();
  const topOffset = cardRect.top - containerRect.top + container.scrollTop - 12;
  const bottomOffset = cardRect.bottom - containerRect.bottom + container.scrollTop + 12;

  if (cardRect.top < containerRect.top || cardRect.height > containerRect.height) {
    container.scrollTo({
      top: Math.max(topOffset, 0),
      behavior: "smooth",
    });
    return;
  }

  if (cardRect.bottom > containerRect.bottom) {
    container.scrollTo({
      top: Math.max(bottomOffset - container.clientHeight, 0),
      behavior: "smooth",
    });
  }
}

function summarizeCollection(items: Array<Record<string, unknown>>) {
  if (items.length === 0) {
    return "暂无记录";
  }

  const firstItem = items[0];
  const keys = Object.keys(firstItem).slice(0, 3);
  return keys.length > 0 ? keys.join(" / ") : "已记录";
}

function plannerLabel(value: unknown) {
  return typeof value === "string" && value ? value : "未定义";
}

function getTraceStatusClass(success: unknown) {
  return success ? "is-success" : "is-failure";
}

function getPlannerTone(action: unknown) {
  return action === "workflow" ? "is-success" : action === "tool" ? "is-warning" : "is-neutral";
}

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isPrimitiveOutput(value: unknown) {
  return (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean" ||
    value === null ||
    value === undefined
  );
}

function formatInlineValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }

  if (value === null || value === undefined) {
    return "暂无内容";
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value);
}

function buildOutputEntries(value: unknown) {
  if (!isObjectRecord(value)) {
    return [];
  }

  return Object.entries(value).map(([key, entryValue]) => ({
    key,
    value: formatInlineValue(entryValue),
  }));
}

function stringifyValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }

  if (value === null || value === undefined) {
    return "暂无内容";
  }

  return JSON.stringify(value, null, 2);
}

watch(
  () => selectedSessionId.value,
  () => {
    expandedTraceIds.value = [];
    expandedEntryId.value = "";
    resetTranscriptFilters();
  },
);

watch(
  () => traceStatusFilter.value,
  (value) => {
    if (value === "failure") {
      expandFailedTraces();
    }
  },
);

watch(
  () => filteredTranscript.value,
  (entries) => {
    if (entries.length === 0) {
      expandedEntryId.value = "";
      return;
    }

    const hasExpandedEntry = entries.some((entry, index) => buildEntryId(entry, index) === expandedEntryId.value);
    if (!hasExpandedEntry && transcriptStatusFilter.value === "failure") {
      expandedEntryId.value = buildEntryId(entries[0], 0);
    }
  },
);

watch(
  () => expandedEntryId.value,
  async (entryId) => {
    if (entryId) {
      await scrollExpandedEntryIntoView();
    }
  },
);
</script>

<template>
  <aside class="inspector-shell">
    <section class="inspector-panel sessions-panel">
      <header class="panel-header">
        <div>
          <p class="panel-eyebrow">Runtime Console</p>
          <h2>会话记录</h2>
        </div>
        <div class="panel-actions">
          <span class="panel-count">{{ sessions.length }} 条</span>
          <button type="button" class="refresh-button" @click="refreshInspector">
            刷新
          </button>
        </div>
      </header>

      <p v-if="sessionsError" class="panel-error">{{ sessionsError }}</p>
      <p v-else-if="sessionsLoading" class="panel-hint">正在同步会话列表...</p>
      <p v-else-if="sessions.length === 0" class="panel-hint">还没有会话记录，先发一条消息试试。</p>

      <div v-else class="session-list">
        <section class="stats-grid session-overview-grid">
          <article
            v-for="stat in sessionPanelStats"
            :key="stat.label"
            class="stat-card session-overview-card"
          >
            <span>{{ stat.label }}</span>
            <strong>{{ stat.value }}</strong>
          </article>
        </section>

        <section class="trace-filters session-filters">
          <label class="filter-field is-search session-search">
            <span>搜索会话</span>
            <input
              v-model="sessionSearch"
              type="text"
              class="filter-input"
              placeholder="搜索 session_id 或 metadata"
            />
          </label>
          <div class="session-filter-meta">
            <span class="session-sort-hint">按最近更新时间倒序</span>
            <button type="button" class="ghost-button" @click="resetSessionSearch">
              清空搜索
            </button>
          </div>
        </section>

        <p v-if="filteredSessions.length === 0" class="panel-hint">
          当前搜索条件下没有匹配到会话。
        </p>

        <button
          v-for="session in filteredSessions"
          :key="session.session_id"
          type="button"
          class="session-card"
          :class="{ 'is-active': session.session_id === selectedSessionId }"
          @click="handleSelectSession(session.session_id)"
        >
          <span class="session-chip">Session</span>
          <strong>{{ session.session_id.slice(0, 8) }}</strong>
          <span class="session-time">更新于 {{ formatTime(session.updated_at) }}</span>
          <span class="session-meta">创建于 {{ formatTime(session.created_at) }}</span>
          <span class="session-meta">
            失败轮次 {{ sessionFailureCounts.get(session.session_id) ?? 0 }}
          </span>
        </button>
      </div>
    </section>

    <section class="inspector-panel transcript-panel">
      <header class="panel-header">
        <div>
          <p class="panel-eyebrow">Transcript</p>
          <h2>{{ selectedSession ? "运行轨迹" : "等待选择会话" }}</h2>
        </div>
        <span v-if="selectedSession" class="panel-count">
          {{ selectedSession.session_id.slice(0, 8) }}
        </span>
      </header>

      <p v-if="transcriptError" class="panel-error">{{ transcriptError }}</p>
      <p v-else-if="transcriptLoading" class="panel-hint">正在展开这次会话的轨迹...</p>
      <p v-else-if="!selectedSessionId" class="panel-hint">选择左侧会话后，这里会展示 transcript 详情。</p>
      <p v-else-if="transcript.length === 0" class="panel-hint">这个会话还没有 transcript 记录。</p>

      <div v-else ref="transcriptListRef" class="transcript-list">
        <section class="stats-grid">
          <article
            v-for="stat in selectedSessionStats"
            :key="stat.label"
            class="stat-card"
          >
            <span>{{ stat.label }}</span>
            <strong>{{ stat.value }}</strong>
          </article>
        </section>

        <section v-if="plannerResult" class="planner-panel">
          <header class="planner-header">
            <div>
              <p class="panel-eyebrow">Planner</p>
              <h3>决策摘要</h3>
            </div>
            <span class="status-badge" :class="getPlannerTone(plannerResult.action)">
              {{ plannerLabel(plannerResult.action) }}
            </span>
          </header>

          <div class="planner-grid">
            <article class="planner-card">
              <span>Decision</span>
              <strong>{{ plannerLabel(plannerResult.action) }}</strong>
            </article>
            <article class="planner-card">
              <span>Tool</span>
              <strong>{{ plannerLabel(plannerResult.tool_name) }}</strong>
            </article>
            <article class="planner-card">
              <span>Workflow</span>
              <strong>{{ plannerLabel(plannerResult.workflow_name) }}</strong>
            </article>
          </div>

        <article class="planner-reason">
            <span>Reason</span>
            <p>{{ plannerLabel(plannerResult.reason) }}</p>
          </article>

          <section v-if="plannerSteps.length > 0" class="planner-steps">
            <header class="subsection-header">
              <h4>Workflow Steps</h4>
              <span>{{ plannerSteps.length }} 步</span>
            </header>
            <div class="planner-step-list">
              <article
                v-for="(step, stepIndex) in plannerSteps"
                :key="`${step.step_name ?? 'step'}-${stepIndex}`"
                class="planner-step-card"
              >
                <div class="planner-step-header">
                  <strong>{{ step.step_name || `step-${stepIndex + 1}` }}</strong>
                  <span class="mini-badge">{{ step.action || "unknown" }}</span>
                </div>
                <p class="planner-step-copy">
                  <span v-if="step.tool_name">调用 {{ step.tool_name }}</span>
                  <span v-else-if="step.prompt_template">基于模版生成回复</span>
                  <span v-else>按当前配置继续执行</span>
                </p>
              </article>
            </div>
          </section>

          <section
            v-if="plannerContext && Object.keys(plannerContext).length > 0"
            class="planner-context"
          >
            <header class="subsection-header">
              <h4>Planner Context</h4>
              <span>{{ Object.keys(plannerContext).length }} 项</span>
            </header>
            <pre class="runtime-code">{{ JSON.stringify(plannerContext, null, 2) }}</pre>
          </section>
        </section>

        <section v-if="workflowTrace.length > 0" class="trace-panel">
          <header class="planner-header">
            <div>
              <p class="panel-eyebrow">Workflow Trace</p>
              <h3>执行时间线</h3>
            </div>
            <div class="panel-actions">
              <span class="panel-count">{{ filteredWorkflowTrace.length }}/{{ workflowTrace.length }} 步</span>
              <button type="button" class="ghost-button" @click="resetTraceFilters">
                清空筛选
              </button>
            </div>
          </header>

          <section class="trace-filters">
            <label class="filter-field">
              <span>状态</span>
              <select v-model="traceStatusFilter" class="filter-select">
                <option value="all">全部</option>
                <option value="success">只看成功</option>
                <option value="failure">只看失败</option>
              </select>
            </label>

            <label class="filter-field">
              <span>动作</span>
              <select v-model="traceActionFilter" class="filter-select">
                <option value="all">全部</option>
                <option value="planner">Planner</option>
                <option value="tool">Tool</option>
                <option value="model">Model</option>
                <option value="workflow">Workflow</option>
              </select>
            </label>

            <label class="filter-field is-search">
              <span>关键词</span>
              <input
                v-model="traceSearch"
                type="text"
                class="filter-input"
                placeholder="搜索 step、action 或摘要"
              />
            </label>
          </section>

          <section class="trace-toolbar">
            <button type="button" class="ghost-button" @click="expandFailedTraces">
              只展开失败步骤
            </button>
            <button type="button" class="ghost-button" @click="expandAllTraces">
              展开全部
            </button>
            <button type="button" class="ghost-button" @click="collapseAllTraces">
              全部收起
            </button>
            <span class="trace-toolbar-hint">
              失败 {{ failedWorkflowTraceCount }} 步
            </span>
          </section>

          <p v-if="filteredWorkflowTrace.length === 0" class="panel-hint">
            当前筛选条件下没有匹配到步骤记录。
          </p>

          <div v-else class="trace-list">
            <article
              v-for="(trace, traceIndex) in filteredWorkflowTrace"
              :key="`${trace.step_name}-${traceIndex}`"
              class="trace-card"
              :class="{ 'is-failure': !trace.success }"
            >
              <div class="trace-rail" />
              <div class="trace-body">
                <header class="trace-header">
                  <div>
                    <span class="trace-step">{{ trace.step_name }}</span>
                    <h4>{{ trace.action }}</h4>
                  </div>
                  <span class="status-badge" :class="getTraceStatusClass(trace.success)">
                    {{ trace.success ? "成功" : "失败" }}
                  </span>
                </header>

                <div class="trace-summary-grid">
                  <article class="trace-summary-card">
                    <span>输入摘要</span>
                    <p>{{ trace.input_summary || "暂无摘要" }}</p>
                  </article>
                  <article class="trace-summary-card">
                    <span>输出摘要</span>
                    <p>{{ trace.output_summary || "暂无摘要" }}</p>
                  </article>
                </div>

                <section
                  v-if="isTraceExpanded(trace, traceIndex)"
                  class="trace-details"
                >
                  <article
                    v-if="isObjectRecord(trace.output)"
                    class="trace-detail-card"
                  >
                    <span>结构化输出</span>
                    <dl class="trace-output-grid">
                      <div
                        v-for="entry in buildOutputEntries(trace.output)"
                        :key="entry.key"
                        class="trace-output-item"
                      >
                        <dt>{{ entry.key }}</dt>
                        <dd>{{ entry.value }}</dd>
                      </div>
                    </dl>
                  </article>
                  <article
                    v-if="Array.isArray(trace.output) || !isPrimitiveOutput(trace.output)"
                    class="trace-detail-card"
                  >
                    <span>完整输出</span>
                    <pre class="runtime-code compact-code">{{ stringifyValue(trace.output) }}</pre>
                  </article>
                  <article
                    v-else
                    class="trace-detail-card"
                  >
                    <span>完整输出</span>
                    <p class="trace-detail-copy">{{ stringifyValue(trace.output) }}</p>
                  </article>
                  <article
                    v-if="trace.error"
                    class="trace-detail-card trace-detail-error"
                  >
                    <span>错误信息</span>
                    <p>{{ trace.error }}</p>
                  </article>
                </section>

                <footer class="trace-footer">
                  <time>{{ formatTime(String(trace.timestamp)) }}</time>
                  <button
                    type="button"
                    class="trace-toggle"
                    @click="toggleTraceDetails(trace, traceIndex)"
                  >
                    {{ isTraceExpanded(trace, traceIndex) ? "收起详情" : "展开详情" }}
                  </button>
                </footer>
              </div>
            </article>
          </div>
        </section>

        <section class="trace-panel transcript-browser">
          <header class="planner-header">
            <div>
              <p class="panel-eyebrow">Transcript Browser</p>
              <h3>对话轮次</h3>
            </div>
            <div class="panel-actions">
              <span class="panel-count">{{ filteredTranscript.length }}/{{ transcript.length }} 轮</span>
              <button type="button" class="ghost-button" @click="resetTranscriptFilters">
                清空筛选
              </button>
            </div>
          </header>

          <section v-if="transcript.length >= 2" class="diff-panel">
            <header class="diff-panel-header">
              <div>
                <p class="panel-eyebrow">Run Diff</p>
                <h4>对比两次运行</h4>
              </div>
              <button
                type="button"
                class="ghost-button"
                :disabled="diffLoading"
                @click="runTranscriptDiff"
              >
                {{ diffLoading ? "对比中…" : "执行对比" }}
              </button>
            </header>
            <div class="diff-controls">
              <label class="filter-field">
                <span>基准</span>
                <select v-model.number="diffBaseIndex" class="filter-select">
                  <option
                    v-for="(_, index) in transcript"
                    :key="`base-${index}`"
                    :value="index"
                  >
                    {{ transcriptRoundLabel(index) }}
                  </option>
                </select>
              </label>
              <label class="filter-field">
                <span>对比</span>
                <select v-model.number="diffCompareIndex" class="filter-select">
                  <option
                    v-for="(_, index) in transcript"
                    :key="`compare-${index}`"
                    :value="index"
                  >
                    {{ transcriptRoundLabel(index) }}
                  </option>
                </select>
              </label>
            </div>
            <p v-if="diffError" class="panel-hint is-error">{{ diffError }}</p>
            <div v-else-if="diffResult" class="diff-result">
              <p class="diff-summary" :class="diffResult.changed ? 'is-changed' : 'is-same'">
                {{ diffResult.changed ? "存在差异" : "两次运行一致" }}
              </p>
              <ul v-if="diffChangedItems.length > 0" class="diff-list">
                <li v-for="item in diffChangedItems" :key="item.field" class="diff-item">
                  <strong>{{ item.field }}</strong>
                  <div class="diff-values">
                    <p><span>基准</span>{{ formatInlineValue(item.base) }}</p>
                    <p><span>对比</span>{{ formatInlineValue(item.compare) }}</p>
                  </div>
                </li>
              </ul>
            </div>
          </section>

          <section class="trace-filters transcript-filters">
            <label class="filter-field">
              <span>状态</span>
              <select v-model="transcriptStatusFilter" class="filter-select">
                <option value="all">全部</option>
                <option value="success">只看成功</option>
                <option value="failure">只看失败</option>
              </select>
            </label>

            <label class="filter-field is-search transcript-search">
              <span>关键词</span>
              <input
                v-model="transcriptSearch"
                type="text"
                class="filter-input"
                placeholder="搜索输入、输出或类型"
              />
            </label>
          </section>

          <p v-if="filteredTranscript.length === 0" class="panel-hint">
            当前筛选条件下没有匹配到 transcript 记录。
          </p>

          <article
            v-for="(entry, index) in filteredTranscript"
            :key="buildEntryId(entry, index)"
            :ref="(element) => setTranscriptCardRef(buildEntryId(entry, index), element)"
            class="transcript-card"
            :class="{ 'is-latest': index === 0 }"
          >
          <header class="transcript-header">
            <div>
              <div class="transcript-meta-line">
                <span class="transcript-type">{{ entry.type }}</span>
                <span v-if="index === 0" class="latest-chip">最近一次</span>
              </div>
              <h3>{{ entry.user_input }}</h3>
            </div>
            <span
              class="status-badge"
              :class="entry.success ? 'is-success' : 'is-failure'"
            >
              {{ entry.success ? "成功" : "失败" }}
            </span>
          </header>

          <p class="transcript-output">
            {{ entry.final_output || "本轮没有最终输出" }}
          </p>

          <div class="transcript-insights">
            <span class="transcript-insight-chip">
              Planner {{ getPlannerAction(entry) }}
            </span>
            <span class="transcript-insight-chip">
              Tool {{ entry.runtime_session.tool_calls.length }}
            </span>
            <span class="transcript-insight-chip">
              Model {{ entry.runtime_session.model_calls.length }}
            </span>
            <span class="transcript-insight-chip">
              Trace {{ entry.runtime_session.workflow_trace.length }}
            </span>
          </div>

          <footer class="transcript-footer">
            <time>{{ formatTime(entry.timestamp) }}</time>
            <button
              type="button"
              class="runtime-toggle"
              @click="toggleRuntime(buildEntryId(entry, index))"
            >
              {{ expandedEntryId === buildEntryId(entry, index) ? "收起运行快照" : "查看运行快照" }}
            </button>
          </footer>

          <section
            v-if="expandedEntryId === buildEntryId(entry, index)"
            class="runtime-details"
          >
            <article class="runtime-group">
              <header>
                <h4>执行概览</h4>
                <span>本轮状态快照</span>
              </header>
              <dl class="overview-grid">
                <div>
                  <dt>Session</dt>
                  <dd>{{ entry.runtime_session.session_id }}</dd>
                </div>
                <div>
                  <dt>输入</dt>
                  <dd>{{ entry.runtime_session.user_input }}</dd>
                </div>
                <div>
                  <dt>输出</dt>
                  <dd>{{ entry.runtime_session.final_output || "暂无输出" }}</dd>
                </div>
                <div>
                  <dt>错误数</dt>
                  <dd>{{ entry.runtime_session.errors.length }}</dd>
                </div>
              </dl>
            </article>

            <div class="runtime-grid">
              <article class="runtime-group">
                <header>
                  <h4>Planner Result</h4>
                  <span>{{ entry.runtime_session.planner_result ? "已生成" : "无" }}</span>
                </header>
                <pre class="runtime-code">{{
                  entry.runtime_session.planner_result
                    ? JSON.stringify(entry.runtime_session.planner_result, null, 2)
                    : "当前没有 planner_result"
                }}</pre>
              </article>

              <article class="runtime-group">
                <header>
                  <h4>Workflow Result</h4>
                  <span>{{ entry.runtime_session.workflow_result ? "已生成" : "无" }}</span>
                </header>
                <pre class="runtime-code">{{
                  entry.runtime_session.workflow_result
                    ? JSON.stringify(entry.runtime_session.workflow_result, null, 2)
                    : "当前没有 workflow_result"
                }}</pre>
              </article>
            </div>

            <div class="runtime-grid">
              <article class="runtime-group">
                <header>
                  <h4>Tool Calls</h4>
                  <span>{{ entry.runtime_session.tool_calls.length }} 次</span>
                </header>
                <p class="runtime-summary">
                  {{ summarizeCollection(entry.runtime_session.tool_calls) }}
                </p>
                <pre class="runtime-code">{{
                  entry.runtime_session.tool_calls.length > 0
                    ? JSON.stringify(entry.runtime_session.tool_calls, null, 2)
                    : "当前没有 tool_calls"
                }}</pre>
              </article>

              <article class="runtime-group">
                <header>
                  <h4>Model Calls</h4>
                  <span>{{ entry.runtime_session.model_calls.length }} 次</span>
                </header>
                <p class="runtime-summary">
                  {{ summarizeCollection(entry.runtime_session.model_calls) }}
                </p>
                <pre class="runtime-code">{{
                  entry.runtime_session.model_calls.length > 0
                    ? JSON.stringify(entry.runtime_session.model_calls, null, 2)
                    : "当前没有 model_calls"
                }}</pre>
              </article>
            </div>

            <article class="runtime-group">
              <header>
                <h4>Workflow Trace</h4>
                <span>{{ entry.runtime_session.workflow_trace.length }} 条</span>
              </header>
              <p class="runtime-summary">
                {{ summarizeCollection(entry.runtime_session.workflow_trace) }}
              </p>
              <pre class="runtime-code">{{
                entry.runtime_session.workflow_trace.length > 0
                  ? JSON.stringify(entry.runtime_session.workflow_trace, null, 2)
                  : "当前没有 workflow_trace"
              }}</pre>
            </article>

            <article
              v-if="(entry.runtime_session.collaboration_trace?.length ?? 0) > 0"
              class="runtime-group"
            >
              <header>
                <h4>协作轨迹</h4>
                <span>{{ entry.runtime_session.collaboration_trace?.length ?? 0 }} 条</span>
              </header>
              <pre class="runtime-code">{{
                JSON.stringify(entry.runtime_session.collaboration_trace, null, 2)
              }}</pre>
            </article>

            <article
              v-if="(entry.runtime_session.deliverables?.length ?? 0) > 0"
              class="runtime-group"
            >
              <header>
                <h4>成果交付</h4>
                <span>{{ entry.runtime_session.deliverables?.length ?? 0 }} 条</span>
              </header>
              <pre class="runtime-code">{{
                JSON.stringify(entry.runtime_session.deliverables, null, 2)
              }}</pre>
            </article>

            <article
              v-if="entry.runtime_session.errors.length > 0"
              class="runtime-group runtime-errors"
            >
              <header>
                <h4>Errors</h4>
                <span>{{ entry.runtime_session.errors.length }} 条</span>
              </header>
              <ul class="error-list">
                <li v-for="error in entry.runtime_session.errors" :key="error">{{ error }}</li>
              </ul>
            </article>
          </section>
          </article>
        </section>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.inspector-shell {
  display: grid;
  grid-template-rows: minmax(280px, 0.9fr) minmax(360px, 1.1fr);
  gap: 18px;
  min-height: 100%;
  height: 100%;
  min-width: 0;
  overflow: hidden;
}

.inspector-panel {
  display: flex;
  flex-direction: column;
  border-radius: 24px;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 248, 240, 0.92)),
    linear-gradient(135deg, rgba(251, 191, 36, 0.08), rgba(14, 165, 233, 0.08));
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
  min-height: 0;
}

.sessions-panel,
.transcript-panel {
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-eyebrow {
  margin: 0 0 4px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #b45309;
}

.panel-header h2 {
  margin: 0;
  font-size: 20px;
  color: #111827;
}

.panel-count {
  align-self: center;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  color: #7c2d12;
  background: rgba(251, 191, 36, 0.16);
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ghost-button {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  color: #334155;
  background: rgba(255, 255, 255, 0.85);
  cursor: pointer;
}

.refresh-button {
  border: none;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  color: #fff;
  background: linear-gradient(135deg, #d97706, #0f766e);
  cursor: pointer;
}

.panel-hint,
.panel-error {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  font-size: 14px;
}

.panel-hint {
  color: #475569;
  background: rgba(241, 245, 249, 0.8);
}

.panel-error {
  color: #b91c1c;
  background: rgba(254, 226, 226, 0.85);
}

.session-list,
.transcript-list {
  display: grid;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.session-list {
  overflow: auto;
  padding-right: 4px;
}

.transcript-list {
  overflow: auto;
  padding-right: 4px;
}

.session-filters {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
}

.session-overview-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.session-overview-card {
  background: linear-gradient(180deg, rgba(255, 250, 245, 0.96), rgba(255, 255, 255, 0.96));
}

.session-search {
  grid-column: span 1;
}

.session-filter-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.session-sort-hint {
  font-size: 12px;
  color: #64748b;
}

.planner-panel,
.trace-panel {
  display: grid;
  gap: 14px;
  border-radius: 20px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(255, 251, 235, 0.96), rgba(255, 255, 255, 0.96));
  border: 1px solid rgba(251, 191, 36, 0.18);
}

.subsection-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.subsection-header h4 {
  margin: 0;
  font-size: 15px;
  color: #111827;
}

.subsection-header span {
  font-size: 12px;
  color: #92400e;
}

.planner-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.planner-header h3 {
  margin: 0;
  font-size: 18px;
  color: #111827;
}

.planner-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.planner-card,
.planner-reason {
  display: grid;
  gap: 8px;
  border-radius: 16px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.planner-card span,
.planner-reason span,
.trace-summary-card span {
  font-size: 12px;
  color: #92400e;
}

.planner-card strong {
  font-size: 18px;
  color: #111827;
  word-break: break-word;
}

.planner-reason p,
.trace-summary-card p {
  margin: 0;
  color: #334155;
  line-height: 1.6;
  word-break: break-word;
}

.planner-steps,
.planner-context {
  display: grid;
  gap: 12px;
}

.planner-step-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.planner-step-card {
  display: grid;
  gap: 8px;
  border-radius: 16px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.planner-step-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.planner-step-header strong {
  color: #111827;
}

.planner-step-copy {
  margin: 0;
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}

.mini-badge {
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  color: #0f766e;
  background: rgba(14, 165, 233, 0.12);
}

.trace-list {
  display: grid;
  gap: 12px;
}

.trace-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.trace-toolbar-hint {
  font-size: 12px;
  color: #64748b;
}

.trace-filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.filter-field {
  display: grid;
  gap: 8px;
}

.filter-field span {
  font-size: 12px;
  color: #92400e;
}

.filter-select,
.filter-input {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.95);
  color: #0f172a;
  outline: none;
}

.filter-field.is-search {
  grid-column: span 1;
}

.trace-card {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 10px;
}

.trace-rail {
  width: 4px;
  border-radius: 999px;
  background: linear-gradient(180deg, #f59e0b, #0f766e);
  justify-self: center;
}

.trace-card.is-failure .trace-rail {
  background: linear-gradient(180deg, #ef4444, #b91c1c);
}

.trace-body {
  display: grid;
  gap: 12px;
  border-radius: 18px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.8);
}

.trace-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.trace-step {
  display: inline-block;
  margin-bottom: 6px;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: rgba(14, 165, 233, 0.12);
  color: #0f766e;
}

.trace-header h4 {
  margin: 0;
  font-size: 16px;
  color: #0f172a;
}

.trace-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.trace-summary-card {
  display: grid;
  gap: 8px;
  border-radius: 14px;
  padding: 12px;
  background: rgba(248, 250, 252, 0.94);
  border: 1px solid rgba(226, 232, 240, 0.88);
}

.trace-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #64748b;
}

.trace-toggle {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  color: #334155;
  background: rgba(255, 255, 255, 0.95);
  cursor: pointer;
}

.trace-details {
  display: grid;
  gap: 10px;
}

.trace-detail-card {
  display: grid;
  gap: 8px;
  border-radius: 14px;
  padding: 12px;
  background: rgba(248, 250, 252, 0.94);
  border: 1px solid rgba(226, 232, 240, 0.88);
}

.trace-detail-card span {
  font-size: 12px;
  color: #92400e;
}

.trace-detail-card p {
  margin: 0;
  color: #991b1b;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.trace-detail-copy {
  color: #334155;
}

.trace-detail-error {
  border-color: rgba(248, 113, 113, 0.24);
  background: rgba(254, 242, 242, 0.96);
}

.trace-output-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.trace-output-item {
  display: grid;
  gap: 6px;
  border-radius: 12px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(226, 232, 240, 0.88);
}

.trace-output-item dt {
  font-size: 12px;
  color: #92400e;
}

.trace-output-item dd {
  margin: 0;
  color: #334155;
  line-height: 1.6;
  word-break: break-word;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.stat-card {
  display: grid;
  gap: 8px;
  border-radius: 16px;
  padding: 14px;
  background: linear-gradient(180deg, rgba(255, 247, 237, 0.96), rgba(255, 255, 255, 0.96));
  border: 1px solid rgba(251, 191, 36, 0.18);
}

.stat-card span {
  font-size: 12px;
  color: #92400e;
}

.stat-card strong {
  font-size: 22px;
  color: #111827;
}

.session-card {
  text-align: left;
  display: grid;
  gap: 6px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.9);
  cursor: pointer;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.session-card:hover,
.session-card.is-active {
  transform: translateY(-1px);
  border-color: rgba(217, 119, 6, 0.45);
  box-shadow: 0 12px 24px rgba(217, 119, 6, 0.12);
}

.session-chip {
  width: fit-content;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  color: #92400e;
  background: rgba(251, 191, 36, 0.18);
}

.session-card strong {
  font-size: 16px;
  color: #111827;
}

.session-time,
.session-meta {
  font-size: 13px;
  color: #64748b;
}

.diff-panel {
  margin-bottom: 16px;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(59, 130, 246, 0.25);
  background: rgba(239, 246, 255, 0.85);
}

.diff-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.diff-panel-header h4 {
  margin: 4px 0 0;
  font-size: 1rem;
}

.diff-controls {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.diff-result {
  margin-top: 12px;
}

.diff-summary {
  margin: 0 0 8px;
  font-weight: 600;
}

.diff-summary.is-changed {
  color: #b45309;
}

.diff-summary.is-same {
  color: #047857;
}

.diff-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.diff-item {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.diff-values {
  display: grid;
  gap: 6px;
  margin-top: 6px;
  font-size: 0.85rem;
}

.diff-values span {
  display: inline-block;
  min-width: 2.5em;
  color: #64748b;
  margin-right: 6px;
}

.panel-hint.is-error {
  color: #dc2626;
}

.transcript-card {
  display: grid;
  gap: 12px;
  border-radius: 18px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.transcript-card.is-latest {
  border-color: rgba(217, 119, 6, 0.35);
  box-shadow: 0 12px 28px rgba(217, 119, 6, 0.12);
}

.transcript-browser {
  gap: 16px;
}

.transcript-filters {
  grid-template-columns: 180px minmax(0, 1fr);
}

.transcript-search {
  grid-column: span 1;
}

.transcript-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.transcript-meta-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}

.transcript-type {
  display: inline-block;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: rgba(14, 165, 233, 0.12);
  color: #0f766e;
}

.latest-chip {
  display: inline-block;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  color: #7c2d12;
  background: rgba(251, 191, 36, 0.18);
}

.transcript-header h3 {
  margin: 0;
  font-size: 16px;
  color: #0f172a;
}

.status-badge {
  height: fit-content;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
}

.status-badge.is-success {
  color: #166534;
  background: rgba(187, 247, 208, 0.7);
}

.status-badge.is-failure {
  color: #991b1b;
  background: rgba(254, 202, 202, 0.75);
}

.transcript-output {
  margin: 0;
  color: #334155;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.transcript-insights {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.transcript-insight-chip {
  display: inline-block;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  color: #475569;
  background: rgba(241, 245, 249, 0.95);
  border: 1px solid rgba(226, 232, 240, 0.88);
}

.transcript-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #64748b;
}

.runtime-toggle {
  border: none;
  border-radius: 999px;
  padding: 8px 12px;
  color: #fff7ed;
  background: linear-gradient(135deg, #c2410c, #0f766e);
  cursor: pointer;
}

.runtime-details {
  display: grid;
  gap: 12px;
}

.runtime-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.runtime-group {
  display: grid;
  gap: 10px;
  border-radius: 18px;
  padding: 14px;
  background: linear-gradient(180deg, rgba(241, 245, 249, 0.6), rgba(255, 255, 255, 0.95));
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.runtime-group header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.runtime-group h4 {
  margin: 0;
  font-size: 15px;
  color: #111827;
}

.runtime-group header span,
.runtime-summary {
  font-size: 12px;
  color: #64748b;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
  margin: 0;
}

.overview-grid dt {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.overview-grid dd {
  margin: 0;
  color: #0f172a;
  word-break: break-word;
}

.runtime-code {
  margin: 0;
  padding: 14px;
  border-radius: 16px;
  overflow: auto;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 12px;
  line-height: 1.6;
}

.compact-code {
  max-height: 220px;
}

.status-badge.is-warning {
  color: #9a3412;
  background: rgba(253, 230, 138, 0.85);
}

.status-badge.is-neutral {
  color: #334155;
  background: rgba(226, 232, 240, 0.85);
}

.runtime-errors {
  border-color: rgba(248, 113, 113, 0.24);
  background: linear-gradient(180deg, rgba(254, 242, 242, 0.96), rgba(255, 255, 255, 0.96));
}

.error-list {
  margin: 0;
  padding-left: 18px;
  color: #991b1b;
}

@media (max-width: 720px) {
  .inspector-shell {
    grid-template-rows: auto auto;
    height: auto;
    overflow: visible;
  }

  .stats-grid,
  .planner-grid,
  .runtime-grid,
  .overview-grid,
  .trace-summary-grid {
    grid-template-columns: 1fr;
  }

  .trace-filters {
    grid-template-columns: 1fr;
  }

  .transcript-filters {
    grid-template-columns: 1fr;
  }

  .session-filters {
    grid-template-columns: 1fr;
  }

  .session-overview-grid {
    grid-template-columns: 1fr;
  }

  .session-filter-meta {
    justify-content: space-between;
  }

  .trace-output-grid {
    grid-template-columns: 1fr;
  }

  .panel-actions {
    align-items: flex-end;
    flex-direction: column;
  }
}
</style>
