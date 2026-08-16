<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps<{ image: string }>()
const emit = defineEmits<{ (e: 'confirm', base64: string): void; (e: 'cancel'): void }>()

const maskRef = ref<HTMLDivElement | null>(null)
const imgRef = ref<HTMLImageElement | null>(null)
const dragging = ref(false)
const sel = ref({ x: 0, y: 0, w: 0, h: 0 })
const startPoint = ref({ x: 0, y: 0 })
const endPoint = ref({ x: 0, y: 0 })

const imgSrc = computed(() => `data:image/png;base64,${props.image}`)

// 把截图缩放到恰好适应窗口并居中（只缩小不放大），选区坐标按显示/原始尺寸换算
function fitImage() {
  const img = imgRef.value
  const mask = maskRef.value
  if (!img || !mask || !img.naturalWidth) return
  const maxW = mask.clientWidth
  const maxH = mask.clientHeight
  const scale = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight, 1)
  img.style.width = Math.round(img.naturalWidth * scale) + 'px'
  img.style.height = Math.round(img.naturalHeight * scale) + 'px'
}

function pos(e: MouseEvent) {
  const rect = imgRef.value!.getBoundingClientRect()
  return { x: e.clientX - rect.left, y: e.clientY - rect.top }
}

function onDown(e: MouseEvent) {
  if (e.button !== 0) return
  dragging.value = true
  startPoint.value = pos(e)
  endPoint.value = pos(e)
  updateSel()
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function onMove(e: MouseEvent) {
  if (!dragging.value) return
  endPoint.value = pos(e)
  updateSel()
}

function onUp() {
  dragging.value = false
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
}

function updateSel() {
  const { x: x1, y: y1 } = startPoint.value
  const { x: x2, y: y2 } = endPoint.value
  sel.value = {
    x: Math.min(x1, x2),
    y: Math.min(y1, y2),
    w: Math.abs(x2 - x1),
    h: Math.abs(y2 - y1),
  }
}

function cropImage(x: number, y: number, w: number, h: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = Math.max(1, Math.round(w))
      canvas.height = Math.max(1, Math.round(h))
      const ctx = canvas.getContext('2d')
      if (!ctx) return reject(new Error('无法创建画布'))
      ctx.drawImage(img, x, y, w, h, 0, 0, canvas.width, canvas.height)
      resolve(canvas.toDataURL('image/jpeg', 0.9).split(',')[1])
    }
    img.onerror = () => reject(new Error('图片加载失败'))
    img.src = imgSrc.value
  })
}

async function onConfirm() {
  const { x, y, w, h } = sel.value
  if (w < 4 || h < 4) {
    emit('cancel')
    return
  }
  // 选区是显示尺寸，裁图需换算回截图原始尺寸
  const img = imgRef.value
  const scaleX = img && img.clientWidth > 0 ? img.naturalWidth / img.clientWidth : 1
  const scaleY = img && img.clientHeight > 0 ? img.naturalHeight / img.clientHeight : 1
  const base64 = await cropImage(
    Math.round(x * scaleX),
    Math.round(y * scaleY),
    Math.round(w * scaleX),
    Math.round(h * scaleY),
  )
  emit('confirm', base64)
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('cancel')
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', fitImage)
  const img = imgRef.value
  if (img) {
    img.onload = fitImage
    if (img.complete) fitImage()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', fitImage)
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mouseup', onUp)
})
</script>

<template>
  <div ref="maskRef" class="shot-mask">
    <div class="shot-wrap" @mousedown.prevent="onDown">
      <img ref="imgRef" :src="imgSrc" alt="全屏截图" class="shot-img" />
      <div
        v-if="sel.w > 0 && sel.h > 0"
        class="shot-sel"
        :style="{ left: sel.x + 'px', top: sel.y + 'px', width: sel.w + 'px', height: sel.h + 'px' }"
      ></div>
    </div>
    <div class="shot-toolbar">
      <a-button type="primary" @click="onConfirm">确认</a-button>
      <a-button @click="emit('cancel')">取消</a-button>
    </div>
  </div>
</template>

<style scoped>
.shot-mask {
  position: fixed;
  inset: 0;
  z-index: 999;
  background:
    radial-gradient(1000px 600px at 50% 30%, rgba(77, 159, 255, 0.08), transparent 60%),
    rgba(3, 6, 14, 0.72);
  backdrop-filter: blur(2px);
  overflow: hidden;
  cursor: crosshair;
  display: flex;
  align-items: center;
  justify-content: center;
}

.shot-wrap {
  position: relative;
  display: inline-block;
  box-shadow: 0 0 0 1px rgba(110, 150, 255, 0.5), 0 0 40px rgba(0, 0, 0, 0.55);
  background: #0a0f1e;
}

.shot-img {
  display: block;
  user-select: none;
  -webkit-user-drag: none;
}

.shot-sel {
  position: absolute;
  border: 1.5px solid #00e0ff;
  background: rgba(0, 224, 255, 0.14);
  box-shadow: inset 0 0 0 1px rgba(0, 224, 255, 0.3), 0 0 18px rgba(0, 224, 255, 0.35);
  pointer-events: none;
}

.shot-toolbar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  background: rgba(15, 26, 48, 0.85);
  backdrop-filter: blur(10px);
  padding: 8px 14px;
  border-radius: 12px;
  border: 1px solid var(--border-strong);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(77, 159, 255, 0.2);
  z-index: 10;
}
</style>
