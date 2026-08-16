<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const recording = ref(false)
const live = ref('')

const MODS = ['ctrl', 'alt', 'shift', 'win']

function keyName(e: KeyboardEvent): string | null {
  const k = e.key
  if (k === 'Control') return 'ctrl'
  if (k === 'Alt') return 'alt'
  if (k === 'Shift') return 'shift'
  if (k === 'Meta' || k === 'OS') return 'win'
  if (k === ' ') return 'space'
  if (k === 'Escape') return 'esc'
  if (k === 'Enter') return 'enter'
  if (k === 'Tab') return 'tab'
  if (k === 'Backspace') return 'backspace'
  if (k === 'Delete') return 'delete'
  const arrowMap: Record<string, string> = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right' }
  if (arrowMap[k]) return arrowMap[k]
  if (/^F\d{1,2}$/.test(k)) return k.toLowerCase()
  if (k.length === 1) return k.toLowerCase()
  return k.toLowerCase()
}

// 从事件上读取当前按住的修饰键（不依赖修饰键的 keydown 是否单独到达）
function heldMods(e: KeyboardEvent): string[] {
  const mods: string[] = []
  if (e.ctrlKey) mods.push('ctrl')
  if (e.altKey) mods.push('alt')
  if (e.shiftKey) mods.push('shift')
  if (e.metaKey) mods.push('win')
  return mods
}

function onKeyDown(e: KeyboardEvent) {
  if (!recording.value) return
  e.preventDefault()
  e.stopPropagation()
  if (e.key === 'Escape') {
    stop()
    return
  }
  const name = keyName(e)
  if (!name) return
  if (MODS.includes(name)) {
    // 仅修饰键：实时显示当前按住组合，等主键按下
    live.value = heldMods(e).join('+')
    return
  }
  // 主键按下：组合 = 修饰键 + 主键
  const combo = [...heldMods(e), name].join('+')
  emit('update:modelValue', combo)
  stop()
}

function start() {
  recording.value = true
  live.value = ''
}

function stop() {
  recording.value = false
  live.value = ''
}

window.addEventListener('keydown', onKeyDown, true)
</script>

<template>
  <div class="hotkey-input" :class="{ recording }" tabindex="0" @click="start" @blur="stop">
    <span v-if="recording" class="placeholder">请按下组合键（Esc 取消）…</span>
    <span v-else-if="live" class="value">{{ live }}</span>
    <span v-else class="value">{{ modelValue || '点击后按下组合键' }}</span>
  </div>
</template>

<style scoped>
.hotkey-input {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 5px 11px;
  font-size: 14px;
  min-height: 32px;
  display: flex;
  align-items: center;
  cursor: text;
  user-select: none;
  outline: none;
  min-width: 200px;
  background: rgba(8, 14, 28, 0.55);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.hotkey-input.recording {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(0, 224, 255, 0.18), 0 0 14px rgba(0, 224, 255, 0.2);
}
.value {
  color: var(--text);
  font-family: 'Consolas', 'Cascadia Mono', monospace;
  letter-spacing: 0.5px;
}
.placeholder {
  color: var(--text-dim);
}
</style>
