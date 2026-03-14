# -*- coding: utf-8 -*-
"""
历史记录持久化：history.json 的读写。
数据目录来自 config.get_data_dir()；单条含 moved_at、original_name、original_path（可选）、
target_folder、target_folder_display、moved_path（移动后完整路径，供托盘与 /open 使用）。
"""
import json
import os
from datetime import datetime
from typing import Any

from config import get_data_dir


def get_history_path() -> str:
    """返回历史记录文件路径：数据目录 + history.json。"""
    return os.path.join(get_data_dir(), "history.json")


def _load_history_raw() -> list[dict[str, Any]]:
    """读取 history.json，返回原始列表；文件不存在或无效则返回 []。"""
    path = get_history_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _save_history(items: list[dict[str, Any]]) -> None:
    """将历史列表写回 history.json（UTF-8）。"""
    path = get_history_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def append_history(
    config: dict[str, Any] | None,
    original_name: str,
    original_path: str,
    target_folder: str,
    target_folder_display: str,
    moved_path: str,
) -> None:
    """
    追加一条历史记录并写回。
    moved_path：移动后文件/文件夹的完整路径，供托盘与 /open 使用。
    """
    items = _load_history_raw()
    items.append({
        "moved_at": datetime.now().isoformat(),
        "original_name": original_name,
        "original_path": original_path,
        "target_folder": target_folder,
        "target_folder_display": target_folder_display,
        "moved_path": moved_path,
    })
    _save_history(items)


def get_recent(config: dict[str, Any] | None, n: int = 10) -> list[dict[str, Any]]:
    """读取历史，按 moved_at 倒序，返回前 n 条。"""
    items = _load_history_raw()
    sorted_items = sorted(
        items,
        key=lambda x: x.get("moved_at", ""),
        reverse=True,
    )
    return sorted_items[:n]


def get_all(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """读取全部历史，按 moved_at 倒序返回。供 /history 页使用。"""
    items = _load_history_raw()
    return sorted(
        items,
        key=lambda x: x.get("moved_at", ""),
        reverse=True,
    )
