# -*- coding: utf-8 -*-
"""
桌面扫描与到期移动：扫描桌面新项入 pending，处理到期项并移动，占用时重试与通知。
"""
import os
import shutil
from datetime import datetime
from typing import Any

from config import load_config
from history_log import append_history
from notify import notify_in_use, notify_moved
from pending import (
    add_pending,
    get_retry_count,
    increment_retry,
    load_pending,
    remove_pending,
)
from rules import resolve_target


def _get_created_at(path: str) -> str:
    """取路径的创建时间（fallback 修改时间），返回 ISO 字符串。"""
    try:
        ts = os.path.getctime(path)
    except OSError:
        ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts).isoformat()


def scan_desktop(config: dict[str, Any]) -> None:
    """
    扫描桌面第一层项（文件+文件夹），排除 exclude_folders 和 desktop.ini。
    若路径不在 pending 的 path 列表中，则取创建时间并 add_pending。
    """
    desktop = config.get("desktop_path") or ""
    if not desktop or not os.path.isdir(desktop):
        return
    exclude = set((config.get("exclude_folders") or [])) | {"desktop.ini"}
    pending_paths = {item.get("path") for item in load_pending(config) if item.get("path")}

    try:
        names = os.listdir(desktop)
    except OSError:
        return

    for name in names:
        if name in exclude:
            continue
        path = os.path.join(desktop, name)
        if not os.path.exists(path):
            continue
        if path in pending_paths:
            continue
        created_at = _get_created_at(path)
        add_pending(config, path, name, created_at)


def process_due(config: dict[str, Any]) -> None:
    """
    处理到期项：解析目标、创建目标目录、移动；失败则重试，满 3 次通知被占用；
    成功则写历史、移除 pending、通知已移动。
    """
    now = datetime.now()
    delay_seconds = (config.get("delay_hours") or 0) * 3600
    desktop = config.get("desktop_path") or ""
    items = load_pending(config)

    for item in items:
        path = item.get("path")
        name = item.get("name")
        created_at_str = item.get("created_at")
        if not path or not name or not created_at_str:
            continue
        if not os.path.exists(path):
            continue
        try:
            created_at = datetime.fromisoformat(created_at_str)
        except (ValueError, TypeError):
            continue
        if (now - created_at).total_seconds() < delay_seconds:
            continue

        is_lnk = name.lower().endswith(".lnk")
        target = resolve_target(name, is_lnk, config)
        if target is None:
            remove_pending(config, path)
            continue

        dest_dir = os.path.join(desktop, target)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError:
            continue
        dest_path = os.path.join(dest_dir, name)

        try:
            shutil.move(path, dest_path)
        except (PermissionError, OSError):
            increment_retry(config, path)
            if get_retry_count(config, path) >= 3:
                notify_in_use(name)
            continue

        target_folder_display = os.path.basename(target) or target
        append_history(
            config,
            original_name=name,
            original_path=path,
            target_folder=dest_dir,
            target_folder_display=target_folder_display,
            moved_path=dest_path,
        )
        remove_pending(config, path)
        notify_moved(name, target_folder_display)


if __name__ == "__main__":
    cfg = load_config()
    scan_desktop(cfg)
    process_due(cfg)
