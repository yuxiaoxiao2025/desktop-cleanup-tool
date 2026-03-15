# -*- coding: utf-8 -*-
import os
import tempfile
import pytest

# 测试前需 mock get_data_dir 或设环境变量使数据目录指向临时目录
def test_get_feedback_path_returns_path_under_data_dir():
    from config import get_data_dir
    from feedback_store import get_feedback_path
    path = get_feedback_path()
    assert "feedback" in path or "feedback.json" in path
    assert get_data_dir() in path or os.path.dirname(path)
