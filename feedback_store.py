# -*- coding: utf-8 -*-
"""反馈库：用户采纳的分类目标持久化，供缓存与规则提炼。"""
import os
from config import get_data_dir


def get_feedback_path() -> str:
    """返回数据目录下的 feedback.json 路径。"""
    return os.path.join(get_data_dir(), "feedback.json")
