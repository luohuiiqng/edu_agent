<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";

import { fetchSessions, fetchTranscript } from "../services/chatApi";
import type { SessionResponse, TranscriptEntryResponse } from "../types/chat";

const props = defineProps<{
  sessionId: string;
}>();

const emit = defineEmits<{
  back: [];
}>();

const session = ref<SessionResponse | null>(null);
const transcript = ref<TranscriptEntryResponse[]>([]);
const pageLoading = ref(false);
const pageError = ref("");
const expandedEntryId = ref("");
const expandedTraceIds = ref<string[]>([]);
const transcriptListRef = ref<HTMLElement | null>(null);
const transcriptCardRefs = ref<Record<string, HTMLElement | null>>({});
const traceStatusFilter = ref<"all" | "success" | "failure">("all");
const traceActionFilter = ref<"all" | "planner" | "tool" | "model" | "workflow">("all");
const traceSearch = ref("");
const transcriptStatusFilter = ref<"all" | "success" | "failure">("all");
const transcriptSearch = ref("");

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

const runtimeSession = computed(() => activeTranscriptEntry.value?.runtime_session ?? null);
const plannerResult = computed(() => runtimeSession.value?.planner_result ?? null);
const plannerSteps = computed(() => {
  const steps = plannerResult.value?.steps;
  return Array.isArray(steps) ? steps : [];
});
const plannerContext = computed(() => {
  const context = plannerResult.value?.context;
  return context && typeof context === "object" ? context : null;
});
const workflowTrace = computed(() => runtimeSession.value?.workflow_trace ?? []);
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

const activeTranscriptIndex = computed(() =>
  filteredTranscript.value.findIndex((entry, index) => buildEntryId(entry, index) === expandedEntryId.value),
);

const canGoPreviousTranscript = computed(
  () => activeTranscriptIndex.value > 0,
);

const canGoNextTranscript = computed(
  () =>
    activeTranscriptIndex.value >= 0 &&
    activeTranscriptIndex.value < filteredTranscript.value.length - 1,
);

const pageStats = computed(() => {
  if (transcript.value.length === 0) {
    return [
      { label: "记录条数", value: "0" },
      { label: "工具调用", value: "0" },
      { label: "模型调用", value: "0" },
      { label: "失败轮次", value: "0" },
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
  const failureCount = transcript.value.filter((entry) => !entry.success).length;

  return [
    { label: "记录条数", value: String(transcript.value.length) },
    { label: "工具调用", value: String(toolCallCount) },
    { label: "模型调用", value: String(modelCallCount) },
    { label: "失败轮次", value: String(failureCount) },
  ];
});

onMounted(async () => {
  await loadPage();
});

watch(
  () => props.sessionId,
  async () => {
    await loadPage();
  },
);

async function loadPage() {
  if (!props.sessionId) {
    return;
  }

  pageLoading.value = true;
  pageError.value = "";

  try {
    const [sessions, transcriptEntries] = await Promise.all([
      fetchSessions(),
      fetchTranscript(props.sessionId),
    ]);
    session.value = sessions.find((item) => item.session_id === props.sessionId) ?? null;
    transcript.value = transcriptEntries;
    expandedEntryId.value =
      transcriptEntries.length > 0 ? buildEntryId(transcriptEntries[0], 0) : "";
    expandedTraceIds.value = [];
    resetTraceFilters();
    resetTranscriptFilters();
    await scrollExpandedEntryIntoView();
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : "会话详情加载失败";
  } finally {
    pageLoading.value = false;
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

function plannerLabel(value: unknown) {
  return typeof value === "string" && value ? value : "未定义";
}

function getPlannerTone(action: unknown) {
  return action === "workflow" ? "is-success" : action === "tool" ? "is-warning" : "is-neutral";
}

function getPlannerAction(entry: TranscriptEntryResponse) {
  const action = entry.runtime_session.planner_result?.action;
  return typeof action === "string" && action ? action : "unknown";
}

function summarizeCollection(items: Array<Record<string, unknown>>) {
  if (items.length === 0) {
    return "暂无记录";
  }

  const firstItem = items[0];
  const keys = Object.keys(firstItem).slice(0, 3);
  return keys.length > 0 ? keys.join(" / ") : "已记录";
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

function getTraceStatusClass(success: unknown) {
  return success ? "is-success" : "is-failure";
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

function setTranscriptCardRef(entryId: string, element: Element | null) {
  transcriptCardRefs.value = {
    ...transcriptCardRefs.value,
    [entryId]: element instanceof HTMLElement ? element : null,
  };
}

async function toggleRuntime(entryId: string) {
  expandedEntryId.value = expandedEntryId.value === entryId ? "" : entryId;
  if (expandedEntryId.value) {
    await scrollExpandedEntryIntoView();
  }
}

async function showPreviousTranscript() {
  if (!canGoPreviousTranscript.value) {
    return;
  }

  const targetIndex = activeTranscriptIndex.value - 1;
  expandedEntryId.value = buildEntryId(filteredTranscript.value[targetIndex], targetIndex);
  await scrollExpandedEntryIntoView();
}

async function showNextTranscript() {
  if (!canGoNextTranscript.value) {
    return;
  }

  const targetIndex = activeTranscriptIndex.value + 1;
  expandedEntryId.value = buildEntryId(filteredTranscript.value[targetIndex], targetIndex);
  await scrollExpandedEntryIntoView();
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
    container.scrollTo({ top: Math.max(topOffset, 0), behavior: "smooth" });
    return;
  }

  if (cardRect.bottom > containerRect.bottom) {
    container.scrollTo({
      top: Math.max(bottomOffset - container.clientHeight, 0),
      behavior: "smooth",
    });
  }
}

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
    if (!hasExpandedEntry) {
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
  <main class="detail-page">
    <section class="detail-shell">
      <header class="detail-header">
        <div class="detail-header-copy">
          <button type="button" class="back-button" @click="emit('back')">
            返回聊天页
          </button>
          <p class="detail-eyebrow">Session Detail</p>
          <h1>完整运行调试台</h1>
          <p class="detail-subtitle">
            查看这次会话的 transcript、planner 决策、workflow 时间线和运行快照。
          </p>
        </div>

        <div class="detail-session-card">
          <span>当前会话</span>
          <strong>{{ session ? session.session_id.slice(0, 8) : props.sessionId.slice(0, 8) }}</strong>
          <small v-if="session">更新于 {{ formatTime(session.updated_at) }}</small>
        </div>
      </header>

      <p v-if="pageError" class="panel-error">{{ pageError }}</p>
      <p v-else-if="pageLoading" class="panel-hint">正在加载会话详情...</p>

      <section v-else class="detail-grid">
        <section class="hero-panel">
          <section class="stats-grid hero-stats-grid">
            <article
              v-for="stat in pageStats"
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
              <span class="trace-toolbar-hint">失败 {{ failedWorkflowTraceCount }} 步</span>
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
        </section>

        <section class="transcript-browser">
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

          <section class="transcript-navigation">
            <button
              type="button"
              class="ghost-button"
              :disabled="!canGoPreviousTranscript"
              @click="showPreviousTranscript"
            >
              上一条
            </button>
            <span class="transcript-navigation-label">
              {{
                activeTranscriptIndex >= 0
                  ? `当前第 ${activeTranscriptIndex + 1} / ${filteredTranscript.length} 条`
                  : "当前没有展开记录"
              }}
            </span>
            <button
              type="button"
              class="ghost-button"
              :disabled="!canGoNextTranscript"
              @click="showNextTranscript"
            >
              下一条
            </button>
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

          <div v-else ref="transcriptListRef" class="transcript-list">
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
          </div>
        </section>
      </section>
    </section>
  </main>
</template>

<style scoped>
.detail-page {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(251, 191, 36, 0.3), transparent 26%),
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.22), transparent 30%),
    linear-gradient(180deg, #fffaf1, #f6fbff 55%, #f8fafc);
}

.detail-shell {
  width: min(1480px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 20px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
  border-radius: 28px;
  padding: 24px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 25px 55px rgba(15, 23, 42, 0.12);
}

.detail-header-copy {
  display: grid;
  gap: 10px;
}

.detail-eyebrow {
  margin: 0;
  color: #b45309;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
}

.detail-header h1 {
  margin: 0;
  font-size: 34px;
  color: #0f172a;
}

.detail-subtitle {
  margin: 0;
  color: #475569;
  max-width: 64ch;
}

.back-button {
  width: fit-content;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  padding: 10px 14px;
  color: #334155;
  background: rgba(255, 255, 255, 0.92);
  cursor: pointer;
}

.detail-session-card {
  display: grid;
  gap: 8px;
  min-width: 180px;
  padding: 16px 18px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(194, 65, 12, 0.12), rgba(15, 118, 110, 0.12));
}

.detail-session-card span,
.detail-session-card small {
  color: #7c2d12;
}

.detail-session-card strong {
  color: #0f172a;
  font-size: 24px;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
  gap: 20px;
  align-items: start;
}

.hero-panel,
.transcript-browser {
  display: grid;
  gap: 16px;
  min-height: 0;
  border-radius: 24px;
  padding: 18px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 248, 240, 0.92)),
    linear-gradient(135deg, rgba(251, 191, 36, 0.08), rgba(14, 165, 233, 0.08));
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.hero-stats-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
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

.panel-eyebrow {
  margin: 0 0 4px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #b45309;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-count {
  align-self: center;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  color: #7c2d12;
  background: rgba(251, 191, 36, 0.16);
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

.stats-grid {
  display: grid;
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
.trace-summary-card span,
.filter-field span {
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

.trace-filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.filter-field {
  display: grid;
  gap: 8px;
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

.trace-list,
.transcript-list {
  display: grid;
  gap: 12px;
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

.trace-summary-card,
.trace-detail-card {
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

.transcript-browser {
  display: grid;
  gap: 16px;
  min-height: 0;
}

.transcript-navigation {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.transcript-navigation-label {
  font-size: 13px;
  color: #64748b;
}

.transcript-filters {
  grid-template-columns: 180px minmax(0, 1fr);
}

.transcript-list {
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
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

.transcript-type,
.latest-chip,
.status-badge {
  display: inline-block;
  border-radius: 999px;
}

.transcript-type {
  padding: 4px 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: rgba(14, 165, 233, 0.12);
  color: #0f766e;
}

.latest-chip {
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

.status-badge.is-warning {
  color: #9a3412;
  background: rgba(253, 230, 138, 0.85);
}

.status-badge.is-neutral {
  color: #334155;
  background: rgba(226, 232, 240, 0.85);
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

.runtime-errors {
  border-color: rgba(248, 113, 113, 0.24);
  background: linear-gradient(180deg, rgba(254, 242, 242, 0.96), rgba(255, 255, 255, 0.96));
}

.error-list {
  margin: 0;
  padding-left: 18px;
  color: #991b1b;
}

@media (max-width: 1080px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .hero-stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .detail-page {
    padding: 10px;
  }

  .detail-header {
    flex-direction: column;
    padding: 16px;
  }

  .detail-header h1 {
    font-size: 26px;
  }

  .hero-stats-grid,
  .planner-grid,
  .runtime-grid,
  .overview-grid,
  .trace-summary-grid,
  .trace-filters,
  .transcript-filters,
  .trace-output-grid {
    grid-template-columns: 1fr;
  }

  .transcript-navigation {
    flex-direction: column;
    align-items: stretch;
  }

  .panel-actions {
    align-items: flex-end;
    flex-direction: column;
  }
}
</style>
