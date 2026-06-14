<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";

import MessageInput from "./MessageInput.vue";
import MessageList from "./MessageList.vue";
import SessionSidebar from "./SessionSidebar.vue";
import { sendChatMessage } from "../services/chatApi";
import type { ChatMessage } from "../types/chat";

function createMessageId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

// Keep a local in-memory message list for Stage 1 (no persistence yet).
const messages = ref<ChatMessage[]>([
  {
    id: createMessageId(),
    role: "assistant",
    content: "你好，我是你的助手。请告诉我你想做什么。",
    timestamp: new Date().toISOString(),
  },
]);

const loading = ref(false);
const errorText = ref("");
const sessionId = ref<string | undefined>(undefined);
const inspectSessionId = ref<string | undefined>(undefined);
const inspectorRefreshKey = ref(0);
const listWrapper = ref<HTMLElement | null>(null);

const emit = defineEmits<{
  openSessionDetail: [sessionId: string];
}>();

// Centralized append function keeps message structure consistent.
function appendMessage(
  role: ChatMessage["role"],
  content: string,
  timestamp = new Date().toISOString(),
  runtime_session?: ChatMessage["runtime_session"],
) {
  messages.value.push({
    id: createMessageId(),
    role,
    content,
    timestamp,
    ...(runtime_session ? { runtime_session } : {}),
  });
}

// Ensure newest message stays visible after each send/receive cycle.
async function scrollToBottom() {
  await nextTick();
  if (listWrapper.value) {
    listWrapper.value.scrollTop = listWrapper.value.scrollHeight;
  }
}

// Main send flow: validate -> optimistic user message -> request -> render assistant message.
async function handleSend(text: string) {
  if (!text.trim()) {
    errorText.value = "请输入消息后再发送";
    return;
  }

  if (text.length > 2000) {
    errorText.value = "消息长度不能超过 2000 个字符";
    return;
  }

  errorText.value = "";
  appendMessage("user", text);
  await scrollToBottom();

  loading.value = true;
  try {
    const result = await sendChatMessage({ message: text, session_id: sessionId.value });
    sessionId.value = result.session_id;
    inspectSessionId.value = result.session_id;
    inspectorRefreshKey.value += 1;
    appendMessage("assistant", result.reply, result.timestamp, result.runtime_session);
  } catch (error) {
    const message = error instanceof Error ? error.message : "网络连接失败，请稍后重试";
    errorText.value = message;
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
}

function handleSessionSelected(selectedSessionId: string) {
  inspectSessionId.value = selectedSessionId;
  emit("openSessionDetail", selectedSessionId);
}

onMounted(() => {
  inspectorRefreshKey.value += 1;
});
</script>

<template>
  <main class="chat-shell">
    <section class="workspace">
      <section class="chat-panel">
        <header class="chat-header">
          <div>
            <p class="chat-eyebrow">LearnChain Studio</p>
            <h1>Agent Playground</h1>
            <p class="chat-subtitle">一边对话，一边查看 session 与 transcript 的真实运行轨迹。</p>
          </div>
          <div class="chat-badge">
            <span>当前会话</span>
            <strong>{{ sessionId ? sessionId.slice(0, 8) : "尚未创建" }}</strong>
          </div>
        </header>

        <div ref="listWrapper" class="chat-history">
          <MessageList :messages="messages" />
        </div>

        <p v-if="errorText" class="error-banner">{{ errorText }}</p>

        <MessageInput :loading="loading" @submit="handleSend" />
      </section>

      <SessionSidebar
        :active-session-id="inspectSessionId"
        :refresh-key="inspectorRefreshKey"
        @open-session-detail="handleSessionSelected"
      />
    </section>
  </main>
</template>

<style scoped>
.chat-shell {
  height: 100vh;
  padding: 24px;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, rgba(251, 191, 36, 0.3), transparent 26%),
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.22), transparent 30%),
    linear-gradient(180deg, #fffaf1, #f6fbff 55%, #f8fafc);
}

.workspace {
  width: min(1400px, 100%);
  height: calc(100vh - 48px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 460px);
  gap: 20px;
  align-items: stretch;
}

.chat-panel {
  display: grid;
  grid-template-rows: auto 1fr auto auto;
  gap: 14px;
  background: rgba(255, 255, 255, 0.68);
  backdrop-filter: blur(14px);
  border-radius: 28px;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 25px 55px rgba(15, 23, 42, 0.12);
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.chat-eyebrow {
  margin: 0 0 8px;
  color: #b45309;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
}

.chat-header h1 {
  margin: 0;
  font-size: 32px;
  color: #0f172a;
}

.chat-subtitle {
  margin: 10px 0 0;
  color: #475569;
  max-width: 56ch;
}

.chat-badge {
  align-self: flex-start;
  display: grid;
  gap: 6px;
  min-width: 140px;
  padding: 12px 14px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(194, 65, 12, 0.12), rgba(15, 118, 110, 0.12));
  color: #7c2d12;
  font-size: 12px;
}

.chat-badge strong {
  color: #0f172a;
  font-size: 15px;
}

.chat-history {
  overflow: auto;
  min-height: 0;
  padding-right: 4px;
  border-radius: 22px;
  padding: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(248, 250, 252, 0.9));
  border: 1px solid rgba(226, 232, 240, 0.7);
}

.error-banner {
  margin: 0;
  color: #b91c1c;
  background: #fee2e2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 14px;
}

@media (max-width: 1080px) {
  .chat-shell {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .workspace {
    grid-template-columns: 1fr;
    height: auto;
  }

  .chat-panel {
    min-height: auto;
    height: auto;
    overflow: visible;
  }
}

@media (max-width: 768px) {
  .chat-shell {
    padding: 10px;
  }

  .chat-panel {
    min-height: auto;
    border-radius: 20px;
    padding: 12px;
  }

  .chat-header {
    flex-direction: column;
  }

  .chat-header h1 {
    font-size: 26px;
  }
}
</style>
