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
    import feedback_store
    monkeypatch.setattr(feedback_store, "get_data_dir", lambda: str(tmp_path))
    from feedback_store import add_feedback, lookup_feedback
    add_feedback(None, file_name="报告.pdf", extension=".pdf", target="投标与结算", original_path="C:\\Users\\x\\Desktop\\报告.pdf")
    found = lookup_feedback(None, file_name="报告.pdf", extension=".pdf")
    assert found is not None
    assert found.get("target") == "投标与结算"
    # 同一 key 再追加一条，应返回最近一条
    add_feedback(None, file_name="报告.pdf", extension=".pdf", target="其他文件夹", original_path="")
    found2 = lookup_feedback(None, file_name="报告.pdf", extension=".pdf")
    assert found2 is not None
    assert found2.get("target") == "其他文件夹"


def test_lookup_feedback_returns_none_when_no_match(tmp_path, monkeypatch):
    import feedback_store
    monkeypatch.setattr(feedback_store, "get_data_dir", lambda: str(tmp_path))
    from feedback_store import add_feedback, lookup_feedback
    add_feedback(None, file_name="a.pdf", extension=".pdf", target="某目录", original_path="")
    assert lookup_feedback(None, file_name="b.pdf", extension=".pdf") is None
    assert lookup_feedback(None, file_name="a.pdf", extension=".docx") is None


def test_get_feedback_by_target(tmp_path, monkeypatch):
    import feedback_store
    monkeypatch.setattr(feedback_store, "get_data_dir", lambda: str(tmp_path))
    from feedback_store import add_feedback, get_feedback_grouped_by_target
    add_feedback(None, "a.pdf", ".pdf", "投标与结算", "")
    add_feedback(None, "b.pdf", ".pdf", "投标与结算", "")
    add_feedback(None, "c.docx", ".docx", "开发与需求", "")
    grouped = get_feedback_grouped_by_target(None)
    assert "投标与结算" in grouped
    assert len(grouped["投标与结算"]) >= 2
    assert "开发与需求" in grouped
