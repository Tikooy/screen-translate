<script setup lang="ts">
import { ref, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import { getSettings, saveSettings, testSettings, type SettingsData } from '../api/settings'
import { TARGET_LANG_OPTIONS } from '../lang'
import HotkeyRecordInput from './HotkeyRecordInput.vue'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'update:open', v: boolean): void; (e: 'saved'): void }>()

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)

const form = ref<SettingsData>({
  translate_provider: 'deepl',
  deepl_api_key: '',
  google_api_key: '',
  openai_api_key: '',
  openai_base_url: 'https://api.openai.com/v1',
  openai_model: 'gpt-4o-mini',
  word_pick_hotkey: 'ctrl+alt+t',
  word_pick_lang: 'ZH',
  region_poll_interval: 2,
  exit_on_close: false,
})

const providerOptions = [
  { label: 'DeepL', value: 'deepl' },
  { label: 'Google Cloud Translation', value: 'google' },
  { label: 'OpenAI 兼容接口', value: 'openai' },
]

async function load() {
  loading.value = true
  try {
    const s = await getSettings()
    form.value = { ...s }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '读取设置失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (v) => {
    if (v) {
      load()
      // 暂停全局热键，避免录制热键时按下旧组合键误触发取词
      fetch('/api/settings/hotkey-pause', { method: 'POST' }).catch(() => {})
    } else {
      fetch('/api/settings/hotkey-resume', { method: 'POST' }).catch(() => {})
    }
  },
)

function providerPatch() {
  // 测试连接只提交引擎相关字段
  return {
    translate_provider: form.value.translate_provider,
    deepl_api_key: form.value.deepl_api_key,
    google_api_key: form.value.google_api_key,
    openai_api_key: form.value.openai_api_key,
    openai_base_url: form.value.openai_base_url,
    openai_model: form.value.openai_model,
  }
}

async function onTest() {
  testing.value = true
  try {
    const r = await testSettings(providerPatch())
    if (r.ok) {
      Message.success(`连接成功，测试翻译结果：${r.sample}`)
    } else {
      Message.error(`连接失败：${r.error}`)
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '测试失败')
  } finally {
    testing.value = false
  }
}

async function onSave() {
  saving.value = true
  try {
    const r = await saveSettings({ ...form.value })
    if (r.ok) {
      Message.success('设置已保存')
      emit('saved')
      emit('update:open', false)
    } else {
      Message.error(r.error || '保存失败')
    }
  } catch (e) {
    Message.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <a-modal
    :visible="props.open"
    :footer="false"
    :mask-closable="false"
    title="设置"
    width="560px"
    @cancel="emit('update:open', false)"
  >
    <div v-if="loading" class="loading">加载中…</div>
    <a-form v-else :model="form" layout="vertical">
      <a-form-item label="翻译引擎">
        <a-radio-group v-model="form.translate_provider" type="button">
          <a-radio v-for="opt in providerOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </a-radio>
        </a-radio-group>
      </a-form-item>

      <template v-if="form.translate_provider === 'deepl'">
        <a-form-item label="DeepL API Key">
          <a-input-password v-model="form.deepl_api_key" placeholder="输入 DeepL API Key" />
        </a-form-item>
      </template>

      <template v-else-if="form.translate_provider === 'google'">
        <a-form-item label="Google API Key">
          <a-input-password v-model="form.google_api_key" placeholder="输入 Google Cloud Translation API Key" />
        </a-form-item>
      </template>

      <template v-else>
        <a-form-item label="API Key">
          <a-input-password v-model="form.openai_api_key" placeholder="输入 API Key（OpenAI/DeepSeek/通义/月之暗面等）" />
        </a-form-item>
        <a-form-item label="Base URL">
          <a-input v-model="form.openai_base_url" placeholder="https://api.openai.com/v1" />
        </a-form-item>
        <a-form-item label="模型">
          <a-input v-model="form.openai_model" placeholder="如 gpt-4o-mini / deepseek-chat / qwen-plus" />
        </a-form-item>
      </template>

      <a-form-item>
        <a-button :loading="testing" @click="onTest">测试连接</a-button>
        <span class="tip">用当前填写的引擎配置做一次测试翻译</span>
      </a-form-item>

      <a-divider />

      <a-form-item label="取词翻译热键">
        <div class="hotkey-row">
          <HotkeyRecordInput v-model="form.word_pick_hotkey" />
          <a-button size="small" @click="form.word_pick_hotkey = 'ctrl+alt+t'">重置为 Ctrl+Alt+T</a-button>
        </div>
      </a-form-item>

      <a-form-item label="取词翻译语言">
        <a-select v-model="form.word_pick_lang" :options="TARGET_LANG_OPTIONS" style="width: 200px" />
      </a-form-item>

      <a-form-item label="区域翻译轮询间隔">
        <a-input-number v-model="form.region_poll_interval" :min="0.5" :max="60" :step="0.5" style="width: 160px" />
        <span class="tip">秒。开始区域翻译后每隔该时长重新截图检测文字是否变化</span>
      </a-form-item>

      <a-form-item label="点击窗口 × 直接退出">
        <a-switch v-model="form.exit_on_close" />
        <span class="tip">开启后点 × 直接退出程序；关闭则最小化到托盘</span>
      </a-form-item>

      <a-form-item>
        <a-button type="primary" :loading="saving" @click="onSave">保存</a-button>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<style scoped>
.loading {
  text-align: center;
  color: var(--text-dim);
  padding: 24px;
}
.tip {
  margin-left: 10px;
  font-size: 12px;
  color: var(--text-dim);
}
.hotkey-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
