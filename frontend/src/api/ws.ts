// 伪流式翻译的 WebSocket 客户端：自动建连/重连，按 task_id 分发消息。

export interface SocketHandler {
  taskId: string
  onChunk: (text: string) => void
  onDone: () => void
  onError: (message: string) => void
}

class TranslationSocket {
  private ws: WebSocket | null = null
  private connecting = false
  private queue: Record<string, unknown>[] = []
  private handlers = new Map<string, SocketHandler>()

  private connect() {
    if (this.ws || this.connecting) return
    this.connecting = true
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws`)
    this.ws = ws

    ws.onopen = () => {
      this.connecting = false
      for (const msg of this.queue) ws.send(JSON.stringify(msg))
      this.queue = []
    }

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data) as { type: string; task_id?: string; text?: string; message?: string }
      if (!msg.task_id) return
      const handler = this.handlers.get(msg.task_id)
      if (!handler) return
      if (msg.type === 'chunk' && msg.text != null) handler.onChunk(msg.text)
      else if (msg.type === 'done') handler.onDone()
      else if (msg.type === 'error' && msg.message) handler.onError(msg.message)
    }

    ws.onclose = () => {
      this.ws = null
      this.connecting = false
    }
    ws.onerror = () => ws.close()
  }

  request(msg: Record<string, unknown>, handler: SocketHandler) {
    this.handlers.set(handler.taskId, handler)
    this.connect()
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(msg))
    else this.queue.push(msg)
  }

  remove(taskId: string) {
    this.handlers.delete(taskId)
  }

  // 取消翻译：移除处理器（忽略后续块），并通知后端停止
  cancel(taskId: string) {
    this.handlers.delete(taskId)
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'cancel', task_id: taskId }))
    }
  }
}

export const socket = new TranslationSocket()
