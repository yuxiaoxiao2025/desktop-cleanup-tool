# -*- coding: utf-8 -*-
"""
Windows 系统通知：桌面整理结果（已移动 / 被占用）的 Toast 提示。
非 Windows 环境下静默跳过，不抛错。
"""
import sys


def _show_toast(title: str, body: str) -> None:
    """在 Windows 上显示 Toast，非 Windows 或异常时静默跳过。"""
    if sys.platform != "win32":
        return
    try:
        from winotify import Notification

        toast = Notification(
            app_id="桌面整理",
            title=title,
            msg=body,
        )
        toast.show()
    except Exception:
        pass


def notify_moved(name: str, target_display: str) -> None:
    """通知：文件/文件夹已移至目标。"""
    _show_toast("桌面整理", f"{name} 已移至 {target_display} 文件夹")


def notify_in_use(name: str) -> None:
    """通知：因被占用未能自动移动，提示用户关闭占用或通过托盘重试。"""
    _show_toast(
        "桌面整理",
        f"{name} 因被占用未能自动移动，请关闭占用程序后等待下次自动重试，或在托盘菜单中点击“重试失败项”。",
    )
