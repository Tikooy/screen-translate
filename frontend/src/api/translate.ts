// 截屏与 OCR 的 HTTP 封装。桌面模式优先走 pywebview 桥，开发模式回退 REST。

declare global {
  interface Window {
    pywebview?: {
      api?: {
        capture_screen?: () => Promise<string>
        open_region?: () => Promise<boolean> | boolean
      }
    }
  }
}

export async function captureScreen(): Promise<string> {
  const bridge = window.pywebview?.api?.capture_screen
  if (typeof bridge === 'function') {
    return await bridge()
  }
  const res = await fetch('/api/screenshot', { method: 'POST' })
  if (!res.ok) throw new Error(`截屏失败：${res.status}`)
  const data = await res.json()
  return data.image as string
}

// 区域翻译：仅桌面模式支持（需要 pywebview 桥呼出透明悬浮框）
export async function openRegion(): Promise<void> {
  const bridge = window.pywebview?.api?.open_region
  if (typeof bridge === 'function') {
    await bridge()
    return
  }
  // 浏览器/开发模式无桌面能力，给出提示即可（由调用方决定是否展示）
  throw new Error('区域翻译需要在桌面应用中打开')
}

export async function ocrImage(imageBase64: string): Promise<string> {
  const res = await fetch('/api/ocr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: imageBase64 }),
  })
  if (!res.ok) {
    const err = (await res.json().catch(() => ({}))) as { detail?: string }
    throw new Error(err.detail || `OCR 请求失败：${res.status}`)
  }
  const data = await res.json()
  return data.text as string
}
