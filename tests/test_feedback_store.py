# -*- coding: utf-8 -*-
import os
import pytest

# 测试前需 mock get_data_dir 或设环境变量使数据目录指向临时目录
def test_get_feedback_path_returns_path_under_data_dir():
    from config import get_data_dir
    from feedback_store import get_feedback_path
    path = get_feedback_path()
    assert os.path.basename(path) == "feedback.json"
    assert path.startswith(get_data_dir())


def test_add_and_lookup_feedback(tmp_path, monkeypatch):
    monkeypatch.setattr("config.get_data_dir", lambda: str(tmp_path))
    from feedback_store import add_feedback, lookup_feedback, get_feedback_path
    add_feedback(None, file_name="报告.pdf", extension=".pdf", target="投标与结算", original_path="C:\\Users\\x\\Desktop\\报告.pdf")
    found = lookup_feedback(None, file_name="报告.pdf", extension=".pdf")
    assert found is not None
    assert found.get("target") == "投标与结算"
