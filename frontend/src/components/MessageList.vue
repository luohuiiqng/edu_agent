<script setup lang="ts">
import type { ChatMessage } from "../types/chat";

defineProps<{
  messages: ChatMessage[];
}>();

function turnHasExtras(message: ChatMessage): boolean {
  const rs = message.runtime_session;
  if (!rs) return false;
  const collab = rs.collaboration_trace?.length ?? 0;
  const dels = rs.deliverables?.length ?? 0;
  const traces = rs.workflow_trace?.length ?? 0;
  return collab > 0 || dels > 0 || traces > 1;
}

function formatDeliverableLine(d: Record<string, unknown>): string {
  const kind = String(d.kind ?? "?");
  const title = String(d.title ?? "");
  const uri = String(d.uri ?? "");
  const shortUri = uri.length > 96 ? `${uri.slice(0, 94)}…` : uri;
  return title ? `[${kind}] ${title}${shortUri ? ` — ${shortUri}` : ""}` : `[${kind}] ${shortUri}`;
}
</script>

<template>
  <div class="message-list" aria-live="polite">
    <div
      v-for="message in messages"
      :key="message.id"
      class="message-row"
      :class="message.role === 'user' ? 'is-user' : 'is-assistant'"
    >
      <article class="message-bubble">
        <header class="message-meta">
          <span>{{ message.role === "user" ? "你" : "助手" }}</span>
          <time>{{ new Date(message.timestamp).toLocaleTimeString() }}</time>
        </header>
        <p class="message-content">{{ message.content }}</p>
        <details
          v-if="message.role === 'assistant' && turnHasExtras(message)"
          class="turn-extras"
        >
          <summary>本回合运行摘要（协作 / 成果）</summary>
          <div class="turn-extras-body">
            <p v-if="(message.runtime_session?.workflow_trace?.length ?? 0) > 1" class="extras-line">
              Workflow 轨迹 {{ message.runtime_session?.workflow_trace?.length }} 条（含 planner）
            </p>
            <template v-if="(message.runtime_session?.collaboration_trace?.length ?? 0) > 0">
              <p class="extras-heading">协作轨迹</p>
              <ul class="extras-list">
                <li
                  v-for="(ev, idx) in message.runtime_session?.collaboration_trace"
                  :key="`c-${idx}`"
                >
                  <strong>{{ String(ev.agent_role ?? "?") }}</strong>
                  — {{ String(ev.summary ?? "").slice(0, 200) }}
                </li>
              </ul>
            </template>
            <template v-if="(message.runtime_session?.deliverables?.length ?? 0) > 0">
              <p class="extras-heading">成果交付</p>
              <ul class="extras-list">
                <li
                  v-for="(d, idx) in message.runtime_session?.deliverables"
                  :key="`d-${idx}`"
                >
                  {{ formatDeliverableLine(d as Record<string, unknown>) }}
                </li>
              </ul>
            </template>
          </div>
        </details>
      </article>
    </div>
  </div>
</template>

<style scoped>
.message-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.message-row {
  display: flex;
}

.message-row.is-user {
  justify-content: flex-end;
}

.message-row.is-assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: min(75ch, 80%);
  border-radius: 16px;
  padding: 10px 14px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
}

.message-row.is-user .message-bubble {
  background: linear-gradient(135deg, #ff8a5c, #ff6b6b);
  color: #fff;
}

.message-row.is-assistant .message-bubble {
  background: #ffffff;
  color: #1f2937;
  border: 1px solid #e5e7eb;
}

.message-meta {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 12px;
  opacity: 0.8;
  margin-bottom: 6px;
}

.message-content {
  margin: 0;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.turn-extras {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed rgba(148, 163, 184, 0.9);
  font-size: 13px;
  color: #475569;
}

.turn-extras summary {
  cursor: pointer;
  font-weight: 600;
  color: #0f766e;
}

.turn-extras-body {
  margin-top: 8px;
  display: grid;
  gap: 8px;
}

.extras-heading {
  margin: 4px 0 0;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #64748b;
}

.extras-line {
  margin: 0;
  font-size: 12px;
}

.extras-list {
  margin: 0;
  padding-left: 18px;
}

.extras-list li {
  margin-bottom: 4px;
}
</style>
