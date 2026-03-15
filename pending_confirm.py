# -*- coding: utf-8 -*-
"""
需用户确认列表：置信度不足时加入，供设置页或 API 展示；用户确认/修改目标后执行移动并写反馈。
当前为内存列表，可选扩展为持久化（如 pending_confirm.json）。
"""
import os
import shutil
from typing import Any

from history_log import append_history
from notify import notify_moved
from pending import remove_pending

import feedback_store

_pending_confirm: list[dict[str, Any]] = []


def get_list() -> list[dict[str, Any]]:
    """返回待确认项列表的副本，每项含 path, name, suggested_target, confidence。"""
    return [dict(item) for item in _pending_confirm]


def add_to_pending_confirm(
    path: str, name: str, suggested_target: str, confidence: float
) -> None:
    """将一项加入需用户确认列表。"""
    _pending_confirm.append({
        "path": path,
        "name": name,
        "suggested_target": suggested_target,
        "confidence": confidence,
    })


def confirm(
    config: dict[str, Any], path: str, final_target: str
) -> tuple[bool, str | None]:
    """
    根据 path 找到待确认项，用 final_target 执行移动并写历史/反馈，从待确认列表移除。
    与 monitor._try_move_item 中成功分支逻辑一致：创建目录、shutil.move、append_history、
    remove_pending、add_feedback、notify_moved。
    :return: (True, None) 成功；(False, error_message) 失败（如未找到、路径不存在、移动异常）。
    """
    item = None
    for i, x in enumerate(_pending_confirm):
        if x.get("path") == path:
            item = _pending_confirm.pop(i)
            break
    if not item:
        return False, "未找到该待确认项"

    name = item.get("name", "")
    if not name:
        return False, "待确认项缺少 name"

    if not os.path.exists(path):
        return False, "源路径不存在"

    desktop = config.get("desktop_path") or ""
    dest_dir = os.path.join(desktop, final_target)
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as e:
        return False, "创建目标目录失败: %s" % e

    dest_path = os.path.join(dest_dir, name)
    try:
        shutil.move(path, dest_path)
    except (PermissionError, OSError) as e:
        _pending_confirm.insert(0, item)
        return False, "移动失败: %s" % e

    target_folder_display = os.path.basename(final_target) or final_target
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

    ext = os.path.splitext(name)[1]
    feedback_store.add_feedback(config, name, ext, final_target, original_path=path)
    return True, None
