# -*- coding: utf-8 -*-
"""反馈库：用户采纳的分类目标持久化，供缓存与规则提炼。"""
import json
import os
import time
from typing import Any

from config import get_data_dir


def get_feedback_path() -> str:
    """返回数据目录下的 feedback.json 路径。"""
    return os.path.join(get_data_dir(), "feedback.json")


def _load_feedback(config: Any) -> list[dict[str, Any]]:
    """读取 get_feedback_path() 的 JSON，返回 list；无文件或无效返回 []。config 仅为与上层 API 一致，内部不使用。"""
    path = get_feedback_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return data


def _save_feedback(config: Any, items: list[dict[str, Any]]) -> None:
    """将反馈列表写回 UTF-8。config 仅为与上层 API 一致，内部不使用。"""
    path = get_feedback_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def add_feedback(
    config: Any,
    file_name: str,
    extension: str,
    target: str,
    original_path: str = "",
    content_summary: str = "",
) -> None:
    """追加一条反馈（含 timestamp）。移动成功后或用户确认/修改目标后执行移动时调用。"""
    items = _load_feedback(config)
    items.append({
        "file_name": file_name,
        "extension": extension,
        "target": target,
        "original_path": original_path,
        "timestamp": time.time(),
        "content_summary": content_summary or "",
    })
    _save_feedback(config, items)


def lookup_feedback(config: Any, file_name: str, extension: str) -> dict[str, Any] | None:
    """从反馈库中查找同名+同扩展名的最近一条，返回该条 dict 或 None。"""
    items = _load_feedback(config)
    for entry in reversed(items):
        if isinstance(entry, dict) and entry.get("file_name") == file_name and entry.get("extension") == extension:
            return entry
    return None
