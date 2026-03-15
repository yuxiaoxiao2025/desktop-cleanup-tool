# -*- coding: utf-8 -*-
"""配置模块测试。"""


def test_default_config_has_smart_classification_keys():
    from config import get_default_config

    cfg = get_default_config()
    assert "smart_classification_enabled" in cfg
    assert "confidence_threshold" in cfg
    assert cfg["confidence_threshold"] >= 0 and cfg["confidence_threshold"] <= 1
