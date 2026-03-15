# -*- coding: utf-8 -*-
"""
待整理列表持久化：pending.json 的读写与增删改。
数据目录来自 config.get_data_dir()，由 monitor 启动时调用 validate_pending 做路径存在性校验。
"""
import json
import os
from datetime import datetime
from typing import Any

from config import get_data_dir


def get_pending_path() -> str:
    """返回待整理列表文件路径：数据目录 + pending.json。"""
    return os.path.join(get_data_dir(), "pending.json")


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    """补全缺省字段：retry_count 缺则 0；added_at 缺则用 created_at（兼容旧数据）。"""
    out = dict(item)
    if "retry_count" not in out:
        out["retry_count"] = 0
    if "added_at" not in out or not out["added_at"]:
        out["added_at"] = out.get("created_at") or ""
    return out


def load_pending(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    读取 pending.json，返回项列表。
    文件不存在或为空则返回 []。
    每项至少包含：path, name, created_at, added_at, retry_count（缺则 0）。
    """
    path = get_pending_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [_normalize_item(item) for item in data if isinstance(item, dict)]


def save_pending(config: dict[str, Any] | None, items: list[dict[str, Any]]) -> None:
    """将待整理列表写回 pending.json（UTF-8）。"""
    path = get_pending_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def add_pending(
    config: dict[str, Any] | None,
    path: str,
    name: str,
    created_at: str,
) -> None:
    """
    添加一项到待整理列表。
    若 path 已存在则跳过；否则追加新项（added_at 为当前时间 ISO），并写回。
    """
    items = load_pending(config)
    if any(item.get("path") == path for item in items):
        return
    items.append({
        "path": path,
        "name": name,
        "created_at": created_at,
        "added_at": datetime.now().isoformat(),
        "retry_count": 0,
    })
    save_pending(config, items)


def remove_pending(config: dict[str, Any] | None, path: str) -> None:
    """从待整理列表中移除 path 对应的项，并写回。"""
    items = load_pending(config)
    items = [item for item in items if item.get("path") != path]
    save_pending(config, items)


def increment_retry(config: dict[str, Any] | None, path: str) -> None:
    """将 path 对应项的 retry_count 加 1，并写回。若不存在则不操作。"""
    items = load_pending(config)
    for item in items:
        if item.get("path") == path:
            item["retry_count"] = item.get("retry_count", 0) + 1
            save_pending(config, items)
            return


def get_retry_count(config: dict[str, Any] | None, path: str) -> int:
    """返回 path 对应项的 retry_count；不存在则返回 0。"""
    items = load_pending(config)
    for item in items:
        if item.get("path") == path:
            return item.get("retry_count", 0)
    return 0


def validate_pending(config: dict[str, Any] | None = None) -> None:
    """
    启动时校验：过滤掉 path 不存在的项并写回。
    由 monitor 在启动时调用。
    """
    items = load_pending(config)
    valid = [item for item in items if os.path.exists(item.get("path", ""))]
    if len(valid) != len(items):
        save_pending(config, valid)
