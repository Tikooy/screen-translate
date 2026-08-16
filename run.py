import base64
import contextlib
import threading
import time

import pystray
import uvicorn
import webview
from PIL import Image, ImageDraw, ImageFont

from backend.config import settings
from backend.main import create_app
from backend.runtime import set_hotkey_service
from backend.services.region import RegionManager
from utils.hotkey import HotkeyService
from utils.screenshot import capture_screen_png


class DesktopApi:
    """暴露给前端 JS 的桌面能力（window.pywebview.api.*）。

    注意：窗口引用用 _window 前缀存放，pywebview 生成 JS API 时会递归遍历
    js_api 对象的属性，若存 self.window 会顺着 native 原生对象走成死循环递归。
    """

    def __init__(self):
        self._window = None
        self._open_region = None  # 由 main() 注入：呼出区域翻译框的回调

    def capture_screen(self) -> str:
        """隐藏窗口抓取全屏后恢复，返回 base64 PNG。"""
        if self._window is None:
            return ""
        self._window.hide()
        time.sleep(0.5)  # 等窗口真正隐藏，避免把自己截进图里
        try:
            data = capture_screen_png()
        finally:
            self._window.show()
        return base64.b64encode(data).decode()

    def open_region(self):
        """主窗口点击"区域翻译"：隐藏主窗口并呼出透明区域翻译框。"""
        if self._window is not None:
            self._window.hide()
        if self._open_region is not None:
            self._open_region()
        return True


class BubbleApi:
    """暴露给取词框 JS 的桌面能力：定位到光标处并显示。

    关闭 / 最小化 / 拖拽 / 缩放均由原生标题栏与边框处理，无需 JS 桥。
    """

    def __init__(self):
        self._window = None

    def move_to(self, x: int, y: int):
        """把取词框移到光标附近并显示（取词框 JS 轮询到新结果时调用）。"""
        if self._window is None:
            return
        self._window.move(x + 12, y + 12)
        self._window.show()


class RegionApi:
    """暴露给区域翻译框 JS 的桌面能力：开始/停止自动翻译、关闭框体。"""

    def __init__(self, manager: RegionManager):
        self._manager = manager
        self._window = None
        self._on_close = None  # 关闭框体后恢复主窗口等收尾回调

    def start(self):
        return self._manager.start()

    def stop(self):
        return self._manager.stop()

    def resize(self, width: int, height: int):
        """按逻辑像素调整框体大小（由右下角缩放手柄拖动调用）。"""
        if self._window is None:
            return
        self._window.resize(int(width), int(height))
        return True

    def close(self):
        """停止自动翻译并隐藏框体（由框内"关闭"按钮调用）。"""
        self._manager.stop()
        if self._on_close is not None:
            self._on_close()
        if self._window is not None:
            self._window.hide()
        return True


class ThreadedUvicornServer(uvicorn.Server):
    """后台线程中运行：uvicorn 0.52 会无条件安装信号处理器，而 signal.signal 只能在主线程调用。"""

    @contextlib.contextmanager
    def capture_signals(self):
        yield


def _make_region_transparent(window) -> None:
    """pywebview 的 transparent=True 只设了 WebView2 背景透明，未设 WinForms Form 的
    BackColor，导致透明窗口露出 Form 默认灰色背景。这里补设 Form 背景为透明。"""
    try:
        import clr

        clr.AddReference("System.Drawing")
        from System.Drawing import Color

        window.native.BackColor = Color.Transparent
    except Exception:
        pass  # 非透明后端或设置失败时静默降级，不影响功能


def make_tray_icon_image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((4, 4, 60, 60), radius=14, fill=(51, 122, 255))
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 34)
    except Exception:
        font = ImageFont.load_default()
    draw.text((32, 32), "译", font=font, fill="white", anchor="mm")
    return img


def main():
    app = create_app()
    host, port = settings.host, settings.port
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = ThreadedUvicornServer(config)
    threading.Thread(target=server.run, daemon=True).start()

    # 主窗口：截图翻译 / 取词配置等
    api = DesktopApi()
    main_window = webview.create_window(
        "在线翻译小工具",
        f"http://{host}:{port}",
        js_api=api,
        width=960,
        height=680,
        min_size=(760, 560),
        background_color="#0a0f1e",
    )
    api._window = main_window

    # 区域翻译：后台循环管理器挂到 app.state，供 /api/region/result 轮询；
    # 窗口由 ensure_region_window 首次呼出时创建（复用，透明置顶不抢焦点）。
    region_manager = RegionManager(app)
    app.state.region = region_manager

    state = {"quitting": False}
    bubble_holder: dict = {"window": None}
    bubble_lock = threading.Lock()
    region_holder: dict = {"window": None}
    region_lock = threading.Lock()

    def show_main_window():
        main_window.show()

    def ensure_bubble_window():
        """首次取词时创建取词框窗口，之后复用。

        取词框带原生标题栏（右上角关闭/最小化、可拖拽）且可调整大小、置顶、
        不抢焦点；以 hidden=True 创建，启动时不出现，取词结果到达后由
        BubbleApi.move_to 移到光标旁显示。取词全程不动主窗口。
        """
        if bubble_holder["window"] is not None:
            return
        with bubble_lock:
            if bubble_holder["window"] is not None:
                return
            bubble_api = BubbleApi()
            bubble_window = webview.create_window(
                "取词翻译",
                f"http://{host}:{port}/bubble.html",
                js_api=bubble_api,
                on_top=True,
                focus=False,
                resizable=True,
                min_size=(320, 200),
                width=420,
                height=240,
                hidden=True,
                background_color="#0b1120",
            )
            bubble_api._window = bubble_window
            bubble_holder["window"] = bubble_window

            def on_bubble_closing():
                """取词框点关闭时隐藏到后台而非销毁，下次取词再弹出。"""
                if not state["quitting"]:
                    bubble_window.hide()
                    return False

            bubble_window.events.closing += on_bubble_closing

    def ensure_region_window():
        """首次点击"区域翻译"时创建透明悬浮框，之后复用。

        框体无边框、透明（透看下方内容）、置顶、不抢焦点；拖拽走框内
        .pywebview-drag-region 标题条（easy_drag=False 避免整窗可拖误触按钮）。
        关闭框体时停止翻译并恢复主窗口。
        """
        if region_holder["window"] is not None:
            return
        with region_lock:
            if region_holder["window"] is not None:
                return
            region_api = RegionApi(region_manager)
            region_window = webview.create_window(
                "区域翻译",
                f"http://{host}:{port}/region.html",
                js_api=region_api,
                on_top=True,
                focus=False,
                resizable=True,
                frameless=True,
                easy_drag=False,
                transparent=True,
                min_size=(240, 150),
                width=460,
                height=260,
                hidden=True,
            )
            region_api._window = region_window
            region_api._on_close = show_main_window
            region_holder["window"] = region_window
            region_manager.attach_window(region_window)
            _make_region_transparent(region_window)

            def on_region_closing():
                """区域框点关闭时：停止翻译、隐藏并恢复主窗口（不销毁，下次复用）。"""
                if not state["quitting"]:
                    region_manager.stop()
                    region_window.hide()
                    show_main_window()
                    return False

            region_window.events.closing += on_region_closing

    def show_region_window():
        """确保区域框已创建并显示。"""
        ensure_region_window()
        if region_holder["window"] is not None:
            region_holder["window"].show()

    api._open_region = show_region_window

    hotkey = HotkeyService(on_pick=ensure_bubble_window)
    # 注册到 runtime，让设置保存 / 打开暂停 / 关闭恢复能热更新全局热键
    set_hotkey_service(hotkey)

    def quit_app(destroy_main: bool = True):
        """退出整个程序：停止托盘与区域翻译、销毁窗口，让 webview.start() 返回、进程结束。

        托盘菜单"退出"与设置"点击 × 直接退出"共用；destroy_main=False 表示主窗口
        正由本次关闭流程关闭，无需（也不应）在此重复销毁。
        """
        state["quitting"] = True
        tray_icon.stop()
        region_manager.stop()
        if bubble_holder["window"] is not None:
            bubble_holder["window"].destroy()
        if region_holder["window"] is not None:
            region_holder["window"].destroy()
        if destroy_main:
            main_window.destroy()

    def on_main_closing():
        """主窗口点关闭时的行为，由设置 EXIT_ON_CLOSE 决定：
        - 开启：直接退出程序（返回 True 允许关闭，同时清理托盘与其他窗口）；
        - 关闭：最小化到托盘（返回 False 取消关闭）。
        """
        if state["quitting"]:
            return  # 退出流程中：允许关闭
        if settings.exit_on_close:
            quit_app(destroy_main=False)
            return True
        tray_icon.visible = True
        main_window.hide()
        return False

    def on_tray_show(icon, item):
        main_window.show()

    def on_tray_pick(icon, item):
        hotkey.trigger_now()

    def on_tray_quit(icon, item):
        quit_app(destroy_main=True)

    tray_icon = pystray.Icon(
        "在线翻译小工具",
        make_tray_icon_image(),
        "在线翻译小工具",
        menu=pystray.Menu(
            pystray.MenuItem("显示主窗口", on_tray_show, default=True),
            pystray.MenuItem("取词翻译", on_tray_pick),
            pystray.MenuItem("退出", on_tray_quit),
        ),
    )
    threading.Thread(target=tray_icon.run, daemon=True).start()

    main_window.events.closing += on_main_closing

    def after_start():
        hotkey.start()

    webview.start(after_start)
    hotkey.stop()


if __name__ == "__main__":
    main()
