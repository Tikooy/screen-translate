import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.streaming import iter_translate

router = APIRouter()

_DONE = object()
_ERROR = object()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    provider = websocket.app.state.provider
    buffered: dict | None = None  # 翻译进行中收到的新消息先缓冲，任务结束后再处理
    try:
        while True:
            if buffered is not None:
                msg = buffered
                buffered = None
            else:
                msg = await websocket.receive_json()

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if msg.get("type") != "translate":
                continue

            task_id = msg.get("task_id", "")
            text = msg.get("text", "")
            target_lang = msg.get("target_lang", "ZH")
            source_lang = msg.get("source_lang")

            if not provider.available():
                await websocket.send_json(
                    {"type": "error", "task_id": task_id, "message": "未配置翻译引擎 API Key，请在右上角设置中填写"}
                )
                continue

            loop = asyncio.get_running_loop()
            queue: asyncio.Queue = asyncio.Queue()
            cancel_event = asyncio.Event()

            def produce():
                try:
                    for chunk in iter_translate(provider, text, target_lang, source_lang):
                        if cancel_event.is_set():
                            break
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as exc:
                    loop.call_soon_threadsafe(queue.put_nowait, (_ERROR, str(exc)))
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, (_DONE, None))

            loop.run_in_executor(None, produce)

            errored = False
            cancelled = False
            while True:
                get_task = asyncio.ensure_future(queue.get())
                recv_task = asyncio.ensure_future(websocket.receive_json())
                done_tasks, pending = await asyncio.wait(
                    [get_task, recv_task], return_when=asyncio.FIRST_COMPLETED
                )
                if get_task in done_tasks:
                    item = get_task.result()
                    if recv_task in done_tasks:
                        buffered = recv_task.result()
                    else:
                        recv_task.cancel()
                    # 控制信号是 (_DONE/None) / (_ERROR/msg) 元组；普通 chunk 是字符串
                    if isinstance(item, tuple) and item[0] is _DONE:
                        break
                    if isinstance(item, tuple) and item[0] is _ERROR:
                        errored = True
                        await websocket.send_json({"type": "error", "task_id": task_id, "message": item[1]})
                        break
                    await websocket.send_json({"type": "chunk", "task_id": task_id, "text": item})
                else:
                    get_task.cancel()
                    other = recv_task.result()
                    if other.get("type") == "cancel":
                        cancel_event.set()
                        cancelled = True
                        break
                    buffered = other

            if not errored:
                if cancelled:
                    await websocket.send_json({"type": "cancelled", "task_id": task_id})
                else:
                    await websocket.send_json({"type": "done", "task_id": task_id})
    except WebSocketDisconnect:
        return
