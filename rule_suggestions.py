# -*- coding: utf-8 -*-
"""从反馈库提炼规则候选，供用户一次性审核后写入 config。"""
from __future__ import annotations

import os
import re
from collections import Counter
from typing import Any


def _tokenize_name(name_without_ext: str) -> list[str]:
    """从去掉扩展名后的文件名中按常见分隔符拆分并取非空词。"""
    if not name_without_ext or not name_without_ext.strip():
        return []
    # 空格、下划线、连字符、点号等作为分隔
    parts = re.split(r"[\s_\-\.]+", name_without_ext.strip())
    return [p for p in parts if len(p) > 0]


def suggest_rules_from_feedback(config: dict[str, Any]) -> list[dict[str, Any]]:
    """
    从反馈库按 target 聚合，启发式提炼规则候选：扩展名直接收集；关键词从文件名（去扩展名）分词取频次高的词。
    返回 list[dict]，每项含 name（target 名）, keywords, extensions, target。不写 config。
    """
    import feedback_store

    grouped = feedback_store.get_feedback_grouped_by_target(config)
    result: list[dict[str, Any]] = []

    for target, entries in grouped.items():
        if not target or not entries:
            continue
        extensions: set[str] = set()
        word_counter: Counter[str] = Counter()

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            ext = entry.get("extension") or ""
            if ext and isinstance(ext, str):
                if not ext.startswith("."):
                    ext = "." + ext
                extensions.add(ext)
            name = entry.get("file_name") or ""
            if name and isinstance(name, str):
                base, _ = os.path.splitext(name)
                for word in _tokenize_name(base):
                    if len(word) >= 2:  # 忽略单字符
                        word_counter[word] += 1

        # 至少提供 extensions 或 keywords 之一
        keywords = [w for w, _ in word_counter.most_common(20) if w]
        item: dict[str, Any] = {
            "name": target,
            "target": target,
            "keywords": keywords,
            "extensions": sorted(extensions),
        }
        result.append(item)

    return result
