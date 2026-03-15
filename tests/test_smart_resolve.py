# -*- coding: utf-8 -*-
"""smart_resolve 向量分类模块测试。"""


def test_classify_target_candidates_exists():
    from smart_resolve import classify_target_candidates

    # 无 key 时允许返回 (None, 0.0) 或跳过调用
    result = classify_target_candidates(
        "报告.pdf", [".pdf"], ["投标与结算", "临时与杂项"]
    )
    assert result is not None
    target, score = result
    assert isinstance(score, (int, float))
