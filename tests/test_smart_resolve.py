# -*- coding: utf-8 -*-
"""smart_resolve 向量分类模块测试。"""


def test_resolve_target_with_feedback_rules_first():
    from smart_resolve import resolve_target_with_feedback

    config = {
        "rules": [
            {"keywords": ["投标"], "extensions": [".pdf"], "target": "投标与结算"}
        ],
        "default_target": "临时与杂项",
    }
    target, confidence, source = resolve_target_with_feedback(
        "投标文件.pdf", False, config
    )
    assert source == "rules"
    assert target == "投标与结算"
    assert confidence >= 0.99


def test_classify_target_candidates_exists():
    from smart_resolve import classify_target_candidates

    # 无 key 时允许返回 (None, 0.0) 或跳过调用
    result = classify_target_candidates(
        "报告.pdf", [".pdf"], ["投标与结算", "临时与杂项"]
    )
    assert result is not None
    target, score = result
    assert isinstance(score, (int, float))
