# -*- coding: utf-8 -*-
"""GET /api/rule-suggestions 与 POST /api/rule-suggestions/apply 的测试。"""
from unittest.mock import patch

import pytest


def test_get_rule_suggestions_returns_suggest_rules_from_feedback_result():
    """GET /api/rule-suggestions 返回 suggest_rules_from_feedback(load_config()) 的 JSON 结果。"""
    from web_server import app

    fake_suggestions = [
        {"name": "投标与结算", "keywords": ["投标", "结算"], "extensions": [".pdf", ".xlsx"], "target": "投标与结算"},
    ]
    with patch("web_server.config_module.load_config") as load_cfg:
        with patch("web_server.suggest_rules_from_feedback") as suggest:
            load_cfg.return_value = {}
            suggest.return_value = fake_suggestions
            client = app.test_client()
            r = client.get("/api/rule-suggestions")
    assert r.status_code == 200
    assert r.get_json() == fake_suggestions


def test_post_rule_suggestions_apply_merges_and_saves():
    """POST /api/rule-suggestions/apply 接收勾选规则列表，合并进 config['rules'] 并 save_config，返回 200。"""
    from web_server import app

    existing_rules = [
        {"name": "已有", "keywords": ["a"], "extensions": [".pdf"], "target": "已有"},
    ]
    cfg = {"rules": existing_rules}
    with patch("web_server.config_module.load_config") as load_cfg:
        with patch("web_server.config_module.save_config") as save_cfg:
            load_cfg.return_value = cfg
            client = app.test_client()
            new_rules = [
                {"name": "新规则", "keywords": ["x"], "extensions": [".doc"], "target": "新规则"},
            ]
            r = client.post(
                "/api/rule-suggestions/apply",
                json={"rules": new_rules},
                content_type="application/json",
            )
    assert r.status_code == 200
    assert save_cfg.called
    call_cfg = save_cfg.call_args[0][0]
    assert "rules" in call_cfg
    # 合并后应包含已有 + 新规则（去重后）
    names = [x["name"] for x in call_cfg["rules"]]
    assert "已有" in names
    assert "新规则" in names
