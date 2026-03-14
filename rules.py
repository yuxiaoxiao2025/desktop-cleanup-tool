# -*- coding: utf-8 -*-
"""
规则匹配模块：根据名称与是否快捷方式解析目标相对路径。
"""
import os
from typing import Any


def _normalize_shortcut_name(name: str) -> str:
    """标准化快捷方式名称以便与白名单比较：统一小写，保证 .lnk 后缀。"""
    s = name.strip()
    if not s.lower().endswith(".lnk"):
        s = s + ".lnk"
    return s.lower()


def _in_whitelist(name: str, whitelist: list[str]) -> bool:
    """判断 name 是否在白名单中（标准化后比较）。"""
    if not whitelist:
        return False
    normalized = _normalize_shortcut_name(name)
    for entry in whitelist:
        if isinstance(entry, str) and _normalize_shortcut_name(entry) == normalized:
            return True
    return False


def resolve_target(name: str, is_lnk: bool, config: dict[str, Any]) -> str | None:
    """
    根据名称与是否快捷方式解析目标相对路径。

    - 若 is_lnk 为 True：名称在 shortcut_whitelist 中（标准化后匹配）则返回 None（不移动）；
      否则返回 config["shortcut_target"]。
    - 否则：按 config["rules"] 顺序匹配，若 name 包含任一 keyword 或扩展名在 extensions 中，
      返回该条 target；未命中则返回 config["default_target"]。
    文件夹无扩展名，仅按 keywords 匹配；扩展名比较统一为小写。
    """
    if is_lnk:
        whitelist = config.get("shortcut_whitelist") or []
        if _in_whitelist(name, whitelist):
            return None
        return config.get("shortcut_target") or "00快捷方式"

    rules = config.get("rules") or []
    ext = os.path.splitext(name)[1].lower()

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        keywords = rule.get("keywords") or []
        extensions = rule.get("extensions") or []
        target = rule.get("target")
        if target is None:
            continue
        # 关键词匹配：名称包含任一 keyword
        for kw in keywords:
            if kw and isinstance(kw, str) and kw in name:
                return target
        # 扩展名匹配：仅当有扩展名时（文件）；文件夹无扩展名
        if ext:
            ext_list = [e.lower() if isinstance(e, str) else "" for e in extensions]
            if ext in ext_list:
                return target

    return config.get("default_target") or "临时与杂项"
