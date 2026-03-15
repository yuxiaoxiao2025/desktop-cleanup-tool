# -*- coding: utf-8 -*-
"""从反馈库生成规则候选 suggest_rules_from_feedback 的测试。"""
import pytest


def test_suggest_rules_from_feedback_returns_list(tmp_path, monkeypatch):
    """suggest_rules_from_feedback 返回 list，每项含 target 与 keywords 或 extensions。"""
    import feedback_store
    from rule_suggestions import suggest_rules_from_feedback

    data_dir = str(tmp_path)
    monkeypatch.setattr(feedback_store, "get_data_dir", lambda: data_dir)

    # 预先写入若干条反馈
    feedback_store.add_feedback(None, "投标书.pdf", ".pdf", "投标与结算", "")
    feedback_store.add_feedback(None, "结算单.xlsx", ".xlsx", "投标与结算", "")
    feedback_store.add_feedback(None, "需求文档.docx", ".docx", "开发与需求", "")

    config = {}
    suggestions = suggest_rules_from_feedback(config)

    assert isinstance(suggestions, list)
    for s in suggestions:
        assert "target" in s
        assert "keywords" in s or "extensions" in s
