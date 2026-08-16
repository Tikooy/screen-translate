<script setup lang="ts">
import { Message } from '@arco-design/web-vue'
import { ref, watch } from 'vue'
import { useTranslateStore } from '../stores/translate'
import { SOURCE_LANG_OPTIONS, TARGET_LANG_OPTIONS } from '../lang'

const store = useTranslateStore()

const statusText: Record<string, string> = {
  idle: '',
  ocr: '正在识别文字…',
  translating: '正在翻译…',
  done: '',
  error: '',
}

// ---- 打字机：译文逐字流出，每字淡入 ----
// 渲染不依赖 Vue 响应式逐字更新（否则每字重渲染会闪），直接对 DOM 追加 span。
const translatedBody = ref<HTMLElement | null>(null)
let twTarget = ''
let twCount = 0
let twRaf = 0
let twLast = 0

function twStep(now: number) {
  twRaf = 0
  const el = translatedBody.value
  if (!el) return
  if (now - twLast < 30) {
    twRaf = requestAnimationFrame(twStep)
    return
  }
  twLast = now
  if (twCount < twTarget.length) {
    const span = document.createElement('span')
    span.className = 'tw-char'
    span.textContent = twTarget[twCount++]
    el.appendChild(span)
    if (twCount < twTarget.length) twRaf = requestAnimationFrame(twStep)
  }
}

function twStart() {
  if (!twRaf && twCount < twTarget.length) {
    twLast = 0
    twRaf = requestAnimationFrame(twStep)
  }
}

function twReset() {
  twTarget = ''
  twCount = 0
  if (twRaf) {
    cancelAnimationFrame(twRaf)
    twRaf = 0
  }
  if (translatedBody.value) translatedBody.value.innerHTML = ''
}

// 译文目标变化：清空则重置，新增则继续逐字播放
watch(
  () => store.translated,
  (v) => {
    if (!v) twReset()
    else {
      twTarget = v
      twStart()
    }
  },
)

// 取消翻译时保留已显示的字，停止继续播放
watch(
  () => store.status,
  (s) => {
    if (s === 'idle' && twRaf) {
      cancelAnimationFrame(twRaf)
      twRaf = 0
    }
  },
)

async function copyTranslated() {
  const text = store.translated
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    Message.success('已复制译文')
    return
  } catch {
    // 剪贴板 API 不可用时回退到 execCommand
  }
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  const ok = document.execCommand('copy')
  document.body.removeChild(ta)
  Message[ok ? 'success' : 'warning'](ok ? '已复制译文' : '复制失败，请手动选择复制')
}
</script>

<template>
  <div class="workspace">
    <!-- 原文 / 译文 左右并排 -->
    <div class="columns">
      <div class="col">
        <div class="col-head">
          <span class="col-title">原文</span>
          <a-select v-model="store.sourceLang" :options="SOURCE_LANG_OPTIONS" size="small" class="lang-select" />
        </div>
        <a-textarea
          v-model="store.source"
          :auto-size="{ minRows: 4, maxRows: 10 }"
          placeholder="可输入或粘贴文字，也可手动修正截图识别结果后点翻译"
          class="source-input"
        />
      </div>
      <div class="col">
        <div class="col-head">
          <span class="col-title">译文</span>
          <a-select v-model="store.targetLang" :options="TARGET_LANG_OPTIONS" size="small" class="lang-select" />
          <a-button size="small" :disabled="!store.translated" @click="copyTranslated">复制</a-button>
        </div>
        <div ref="translatedBody" class="translated-body" :class="{ streaming: store.status === 'translating' }"></div>
      </div>
    </div>

    <div class="actions">
      <a-button
        type="primary"
        :loading="store.status === 'translating'"
        :disabled="!store.source.trim() || store.status === 'translating'"
        @click="store.translateCurrent()"
      >
        翻译
      </a-button>
      <a-button v-if="store.status === 'translating'" @click="store.cancelTranslation()">取消</a-button>
    </div>

    <a-alert v-if="store.status === 'error'" type="error" class="status">{{ store.error }}</a-alert>
    <div v-else-if="statusText[store.status]" class="status loading">{{ statusText[store.status] }}</div>
  </div>
</template>

<style scoped>
.workspace {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
  border-radius: 16px;
  background: var(--panel);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.04);
  position: relative;
}

.workspace::before {
  content: '';
  position: absolute;
  top: 0;
  left: 12%;
  right: 12%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.6;
}

.columns {
  display: flex;
  gap: 14px;
}

.col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.col-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.col-title {
  font-size: 12px;
  letter-spacing: 1.5px;
  color: var(--accent);
  font-weight: 700;
  text-transform: uppercase;
}

.lang-select {
  width: 120px;
}

.translated-body {
  flex: 1;
  min-height: 112px;
  padding: 10px 12px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
  user-select: text;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: rgba(8, 14, 28, 0.6);
}

/* 原文输入框与译文框对齐。
   Arco 的 a-textarea 结构：外层 wrapper（边框/背景/圆角）+ 内层 textarea（内边距/行高），
   因此分别覆盖两层，使整体尺寸与译文框完全一致（含 auto-size 的 4 行初始高度 ≈ 112px）。 */
:deep(.source-input) {
  flex: 1;
  min-height: 112px;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  background: rgba(8, 14, 28, 0.6) !important;
}
:deep(.source-input textarea) {
  padding: 10px 12px !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
  color: var(--text) !important;
  resize: none !important;
}
:deep(.source-input:focus-within) {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(0, 224, 255, 0.15) !important;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}

.actions .arco-btn-primary {
  box-shadow: 0 0 20px rgba(77, 159, 255, 0.35);
}

.status {
  margin-top: 2px;
}

.loading {
  text-align: center;
  color: var(--text-dim);
  padding: 6px;
  font-size: 13px;
}

.translated-body.streaming::after {
  content: '▍';
  color: var(--accent);
  margin-left: 2px;
  animation: blink 1s step-start infinite;
}

.tw-char {
  animation: tw-in 0.18s ease-out;
}

@keyframes tw-in {
  from {
    opacity: 0;
    transform: translateY(1px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}
</style>
