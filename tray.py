# -*- coding: utf-8 -*-
"""
托盘图标与右键菜单：pystray 图标、历史子菜单、更多/设置/重试/暂停/学习/退出，tooltip 状态。
"""
import os
import subprocess
import threading
import webbrowser
from typing import Any, Callable

import pystray
from PIL import Image, ImageDraw

from config import load_config, save_config
import history_log
import monitor
from pending import load_pending


def _create_icon_image() -> Image.Image:
    """无 icon.png 时用 Pillow 画 64x64 简单图标（字母 D）。"""
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
    if os.path.isfile(icon_path):
        img = Image.open(icon_path).copy()
        return img.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 圆角矩形背景 + 字母 D 的简化（矩形块）
    draw.rounded_rectangle([4, 4, size - 4, size - 4], radius=8, fill=(66, 133, 244, 255), outline=(50, 100, 200, 255))
    draw.rectangle([16, 18, 28, 46], fill=(255, 255, 255, 255))  # D 竖
    draw.rectangle([28, 18, 46, 26], fill=(255, 255, 255, 255))
    draw.rectangle([28, 38, 46, 46], fill=(255, 255, 255, 255))
    draw.rectangle([38, 26, 46, 38], fill=(255, 255, 255, 255))
    return img


def _open_in_explorer(entry: dict[str, Any]) -> None:
    """用 explorer /select 打开目标并选中文件（Windows）。"""
    moved = entry.get("moved_path") or ""
    if not moved:
        target_folder = entry.get("target_folder") or ""
        name = entry.get("original_name") or ""
        moved = os.path.join(target_folder, name)
    if not moved or not os.path.exists(moved):
        return
    path = os.path.normpath(moved)
    try:
        subprocess.run(["explorer", "/select," + path], check=False, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
    except Exception:
        pass


def learn_from_desktop(config: dict[str, Any]) -> None:
    """
    从桌面学习：扫描 desktop_path 第一层目录（排除 exclude_folders）得文件夹列表；
    扫描桌面根目录 .lnk 文件名更新 shortcut_whitelist；写回 save_config。
    """
    desktop = config.get("desktop_path") or ""
    if not desktop or not os.path.isdir(desktop):
        return
    exclude = set(config.get("exclude_folders") or [])
    try:
        names = os.listdir(desktop)
    except OSError:
        return
    folders = []
    lnk_names = []
    for name in names:
        if name in exclude or name == "desktop.ini":
            continue
        path = os.path.join(desktop, name)
        if not os.path.exists(path):
            continue
        if os.path.isdir(path):
            folders.append(name)
        elif name.lower().endswith(".lnk"):
            lnk_names.append(name)
    config["shortcut_whitelist"] = sorted(lnk_names)
    if "target_candidates" not in config:
        config["target_candidates"] = []
    config["target_candidates"] = sorted(folders)
    save_config(config)


def _build_tooltip(config_ref: list, get_pending: Callable[[], list] | None) -> str:
    base = "桌面整理"
    cfg = config_ref[0] if config_ref else {}
    if cfg.get("monitor_paused"):
        return f"{base} - 已暂停"
    pending = get_pending() if get_pending else load_pending(cfg)
    n = len(pending)
    if n > 0:
        return f"{base} - 运行中（{n} 项待整理）"
    return f"{base} - 运行中"


def run_tray(
    config_ref: list[dict[str, Any]],
    port: int,
    stop_event: threading.Event,
    get_pending: Callable[[], list] | None = None,
) -> None:
    """
    运行托盘图标与菜单，阻塞直到 stop_event 被 set 或用户选「退出」。
    config_ref: 单元素列表 [config]，便于菜单内读写并 save_config。
    get_pending: 可选，返回当前待整理列表用于 tooltip；缺省用 pending.load_pending(config_ref[0])。
    """
    def get_cfg() -> dict[str, Any]:
        return config_ref[0] if config_ref else load_config()

    def history_items() -> list:
        cfg = get_cfg()
        recent = history_log.get_recent(cfg, 10)
        if not recent:
            return [pystray.MenuItem("（无记录）", lambda: None)]
        return [
            pystray.MenuItem(
                f"{e.get('original_name', '')} → {e.get('target_folder_display', '')}",
                lambda e=e: _open_in_explorer(e),
            )
            for e in recent
        ]

    def more(_: pystray.Icon) -> None:
        webbrowser.open(f"http://127.0.0.1:{port}/history")

    def retry(_: pystray.Icon) -> None:
        monitor.retry_failed(get_cfg())

    def toggle_pause(icon: pystray.Icon, _: Any) -> None:
        cfg = get_cfg()
        cfg["monitor_paused"] = not cfg.get("monitor_paused", False)
        save_config(cfg)
        icon.title = _build_tooltip(config_ref, get_pending)
        try:
            icon.update_menu()
        except Exception:
            pass

    def settings(_: pystray.Icon) -> None:
        webbrowser.open(f"http://127.0.0.1:{port}/settings")

    def learn(_: pystray.Icon) -> None:
        learn_from_desktop(get_cfg())

    def quit_app(icon: pystray.Icon, _: Any) -> None:
        stop_event.set()
        icon.stop()

    def is_paused() -> bool:
        return bool(get_cfg().get("monitor_paused"))

    # 暂停/恢复：根据状态只显示其一，菜单文案随之切换
    menu = pystray.Menu(
        pystray.MenuItem("历史记录", pystray.Menu(lambda: history_items())),
        pystray.MenuItem("更多", more),
        pystray.MenuItem("重试失败项", retry),
        pystray.MenuItem(
            "暂停监控",
            toggle_pause,
            visible=lambda _: not is_paused(),
        ),
        pystray.MenuItem(
            "恢复监控",
            toggle_pause,
            visible=lambda _: is_paused(),
        ),
        pystray.MenuItem("设置", settings),
        pystray.MenuItem("从桌面学习", learn),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", quit_app),
    )

    image = _create_icon_image()
    title = _build_tooltip(config_ref, get_pending)
    icon = pystray.Icon("desktop_cleanup", image, title, menu)
    icon.run()


if __name__ == "__main__":
    cfg = load_config()
    config_ref = [cfg]
    ev = threading.Event()
    run_tray(config_ref, port=5000, stop_event=ev, get_pending=None)
