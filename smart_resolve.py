# -*- coding: utf-8 -*-
"""
向量分类模块：零样本选目标与置信度。
仅向量相关逻辑，不依赖 feedback_store。
"""
from __future__ import annotations

from typing import Tuple

import numpy as np


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """计算余弦相似度。"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def classify_target_candidates(
    item_text: str,
    extensions: list[str],
    target_folders: list[str],
) -> Tuple[str | None, float]:
    """
    基于向量零样本分类，从候选目标文件夹中选出最匹配的一个及置信度。

    :param item_text: 当前项描述文本（如文件名+扩展名）
    :param extensions: 扩展名列表（用于日志，本函数内未使用）
    :param target_folders: 目标文件夹名列表（作为标签）
    :return: (best_target, best_score)，若无 API Key 或调用异常则返回 (None, 0.0)
    """
    if not target_folders:
        return (None, 0.0)

    try:
        import dashscope
    except ImportError:
        return (None, 0.0)

    try:
        resp = dashscope.TextEmbedding.call(
            model="text-embedding-v4",
            input=[item_text] + target_folders,
            dimension=1024,
        )
    except Exception:
        return (None, 0.0)

    if resp is None or not hasattr(resp, "output") or not resp.output:
        return (None, 0.0)

    embeddings = resp.output.get("embeddings")
    if not embeddings or len(embeddings) != 1 + len(target_folders):
        return (None, 0.0)

    text_embedding = np.array(embeddings[0]["embedding"])
    label_embeddings = [np.array(emb["embedding"]) for emb in embeddings[1:]]
    scores = [
        _cosine_similarity(text_embedding, label_emb)
        for label_emb in label_embeddings
    ]
    best_idx = int(np.argmax(scores))
    return (target_folders[best_idx], float(scores[best_idx]))
