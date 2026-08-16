import { defineStore } from 'pinia'
import { ref } from 'vue'
import { captureScreen } from '../api/translate'

export const useScreenshotStore = defineStore('screenshot', () => {
  const visible = ref(false)
  const imageBase64 = ref('')
  const capturing = ref(false)

  async function start() {
    capturing.value = true
    try {
      imageBase64.value = await captureScreen()
      visible.value = true
    } finally {
      capturing.value = false
    }
  }

  function close() {
    visible.value = false
    imageBase64.value = ''
  }

  return { visible, imageBase64, capturing, start, close }
})
