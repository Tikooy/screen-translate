import { defineStore } from 'pinia'
import { ref } from 'vue'
import { socket } from '../api/ws'
import { ocrImage } from '../api/translate'

export type TranslateStatus = 'idle' | 'ocr' | 'translating' | 'done' | 'error'

export const useTranslateStore = defineStore('translate', () => {
  const source = ref('')
  const translated = ref('')
  const status = ref<TranslateStatus>('idle')
  const error = ref('')
  const targetLang = ref('ZH')
  const sourceLang = ref('auto') // 'auto'=不传 source_lang，由 DeepL 自动识别
  const cropImage = ref('') // 截图裁剪区域 base64，用于相框展示
  let taskSeq = 0
  let currentTaskId = ''

  function reset() {
    source.value = ''
    translated.value = ''
    error.value = ''
    status.value = 'idle'
    cropImage.value = ''
  }

  function translateText(text: string) {
    source.value = text
    translated.value = ''
    error.value = ''
    status.value = 'translating'
    const taskId = `t${Date.now()}_${taskSeq++}`
    currentTaskId = taskId
    socket.request(
      {
        type: 'translate',
        task_id: taskId,
        text,
        target_lang: targetLang.value,
        source_lang: sourceLang.value === 'auto' ? null : sourceLang.value,
      },
      {
        taskId,
        onChunk: (t) => {
          translated.value += t
        },
        onDone: () => {
          currentTaskId = ''
          status.value = 'done'
        },
        onError: (m) => {
          currentTaskId = ''
          status.value = 'error'
          error.value = m
        },
      },
    )
  }

  function cancelTranslation() {
    if (status.value === 'translating' && currentTaskId) {
      socket.cancel(currentTaskId)
      currentTaskId = ''
      status.value = 'idle' // 保留已输出的部分译文，回到可重新翻译状态
    }
  }

  // 手动触发翻译（原文可编辑，翻译前用当前原文内容）
  function translateCurrent() {
    if (!source.value.trim() || status.value === 'translating') return
    translateText(source.value)
  }

  async function screenshotFlow(imageBase64: string) {
    cropImage.value = imageBase64
    status.value = 'ocr'
    try {
      const text = await ocrImage(imageBase64)
      // 识别后只填原文、不自动翻译，等用户确认/修正后点"翻译"
      source.value = text
      translated.value = ''
      error.value = ''
      status.value = 'idle'
    } catch (e: unknown) {
      status.value = 'error'
      error.value = e instanceof Error ? e.message : String(e)
    }
  }

  return {
    source,
    translated,
    status,
    error,
    targetLang,
    sourceLang,
    cropImage,
    reset,
    translateText,
    translateCurrent,
    cancelTranslation,
    screenshotFlow,
  }
})
