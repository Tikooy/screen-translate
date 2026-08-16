<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { useTranslateStore } from './stores/translate'
import { useScreenshotStore } from './stores/screenshot'
import { openRegion } from './api/translate'
import ScreenshotView from './components/ScreenshotView.vue'
import TranslationPanel from './components/TranslationPanel.vue'
import SettingsModal from './components/SettingsModal.vue'

const translateStore = useTranslateStore()
const screenshotStore = useScreenshotStore()

const keyMissing = ref(false)
const hotkey = ref('')
const settingsOpen = ref(false)
const regionOpening = ref(false)

const shotFrameSrc = computed(() =>
  translateStore.cropImage ? `data:image/jpeg;base64,${translateStore.cropImage}` : '',
)

async function refreshHealth() {
  try {
    const res = await fetch('/api/health')
    const data = (await res.json()) as { provider?: string; word_pick_hotkey?: string }
    keyMissing.value = data.provider === 'MissingKeyProvider'
    hotkey.value = data.word_pick_hotkey ?? ''
  } catch {
    keyMissing.value = false
  }
}

async function onScreenshot() {
  translateStore.reset()
  await screenshotStore.start()
}

async function onConfirm(imageBase64: string) {
  screenshotStore.close()
  await translateStore.screenshotFlow(imageBase64)
}

async function onRegion() {
  regionOpening.value = true
  try {
    await openRegion()
  } catch (e) {
    Message.info(e instanceof Error ? e.message : '区域翻译需要在桌面应用中打开')
  } finally {
    regionOpening.value = false
  }
}

onMounted(refreshHealth)
</script>

<template>
  <a-layout class="app">
    <a-layout-header class="app-header">
      <div class="brand">
        <span class="brand-logo">译</span>
        <span class="app-title">在线翻译小工具</span>
        <span class="app-subtitle">OCR · AI 翻译</span>
      </div>
      <a-button type="text" class="settings-btn" title="设置" @click="settingsOpen = true">
        ⚙
      </a-button>
    </a-layout-header>

    <a-layout-content class="app-body">
      <a-alert v-if="keyMissing" type="warning" class="key-alert">
        未配置所选翻译引擎的 API Key，翻译暂不可用。请点击右上角设置图标填写。
      </a-alert>

      <div class="shot-frame">
        <img v-if="translateStore.cropImage" :src="shotFrameSrc" alt="截图区域" class="shot-frame-img" />
        <div v-else class="shot-frame-empty">截图翻译后，所选区域将显示在这里</div>
      </div>

      <div class="hero">
        <div class="hero-btns">
          <a-button type="primary" size="large" :loading="screenshotStore.capturing" @click="onScreenshot">
            截图翻译
          </a-button>
          <a-button type="outline" size="large" :loading="regionOpening" @click="onRegion">
            区域翻译
          </a-button>
        </div>
        <p class="hint">截图翻译：框选屏幕任意区域，识别文字并翻译为所选语言</p>
        <p class="hint">区域翻译：呼出透明悬浮框，覆盖到要翻译的地方后点击「开始」，自动识别并翻译，文字变化时自动跟进</p>
        <p v-if="hotkey" class="hint">在任意应用选中文字后按 <b>{{ hotkey }}</b>，即可划词翻译</p>
      </div>

      <TranslationPanel />
    </a-layout-content>

    <ScreenshotView
      v-if="screenshotStore.visible"
      :image="screenshotStore.imageBase64"
      @confirm="onConfirm"
      @cancel="screenshotStore.close"
    />

    <SettingsModal :open="settingsOpen" @update:open="(v: boolean) => (settingsOpen = v)" @saved="refreshHealth" />
  </a-layout>
</template>
