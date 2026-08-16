"""进程内运行时共享引用：让后端设置接口能通知前台组件（热键服务等）热更新。"""

hotkey_service = None


def set_hotkey_service(service) -> None:
    global hotkey_service
    hotkey_service = service
