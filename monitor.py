# -*- coding: utf-8 -*-
"""
桌面扫描与到期移动：扫描桌面新项入 pending，处理到期项并移动，占用时重试与通知。
监控循环 run_loop 与重试失败项 retry_failed。
"""
import os
import shutil
import threading
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
    validate_pending,
)
from rules import resolve_target


def _try_move_item(config: dict[str, Any], item: dict[str, Any]) -> bool:
    """
    对单条待整理项执行「解析目标 → 创建目录 → 移动」。
    成功或无法解析目标时移除 pending 并返回 True；移动失败时增加重试并返回 False。
    """
    path = item.get("path")
    name = item.get("name")
    if not path or not name:
        return True
    if not os.path.exists(path):
        remove_pending(config, path)
        return True
    is_lnk = name.lower().endswith(".lnk")
    target = resolve_target(name, is_lnk, config)
    if target is None:
        remove_pending(config, path)
        return True
    dest_dir = os.path.join(config.get("desktop_path") or "", target)
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError:
        return False
    dest_path = os.path.join(dest_dir, name)
    try:
        shutil.move(path, dest_path)
    except (PermissionError, OSError):
        increment_retry(config, path)
        if get_retry_count(config, path) >= 3:
            notify_in_use(name)
        return False
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
    return True


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
        _try_move_item(config, item)


def run_loop(config: dict[str, Any], stop_event: threading.Event) -> None:
    """
    监控循环：未暂停时校验 pending 路径、扫描桌面、处理到期项，然后等待间隔；
    暂停时仅等待 60 秒。循环直到 stop_event 被 set。
    """
    interval = config.get("monitor_interval_seconds", 600)
    pause_wait = 60
    while not stop_event.is_set():
        if config.get("monitor_paused"):
            stop_event.wait(pause_wait)
            continue
        validate_pending(config)
        scan_desktop(config)
        process_due(config)
        stop_event.wait(interval)


def retry_failed(config: dict[str, Any]) -> None:
    """
    对 pending 中 retry_count > 0 的项再执行一次「解析目标 → 移动」。
    成功则移除、写历史、通知；失败则 increment_retry，满 3 次则 notify_in_use。
    """
    items = load_pending(config)
    for item in items:
        if (item.get("retry_count") or 0) <= 0:
            continue
        _try_move_item(config, item)


if __name__ == "__main__":
    cfg = load_config()
    scan_desktop(cfg)
    process_due(cfg)
