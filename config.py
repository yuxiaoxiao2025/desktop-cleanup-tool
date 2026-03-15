# -*- coding: utf-8 -*-
"""
配置模块：数据目录、config.yaml 读写与默认配置。
"""
import os
from typing import Any

import yaml

# 数据目录：%APPDATA%\DesktopCleanup
_DATA_DIR: str | None = None


def get_data_dir() -> str:
    """返回数据目录路径；不存在则创建。供 config、pending、history_log 等共用。"""
    global _DATA_DIR
    if _DATA_DIR is None:
        appdata = os.environ.get("APPDATA", "")
        _DATA_DIR = os.path.join(appdata, "DesktopCleanup")
        os.makedirs(_DATA_DIR, exist_ok=True)
    return _DATA_DIR


def get_config_path() -> str:
    """返回数据目录下的 config.yaml 路径。"""
    return os.path.join(get_data_dir(), "config.yaml")


def get_default_config() -> dict[str, Any]:
    """返回内置默认配置字典。"""
    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    return {
        "desktop_path": desktop,
        "delay_hours": 24,
        "shortcut_whitelist": [
            "Cursor.lnk",
            "Kimi.lnk",
            "Kiro.lnk",
            "纳米AI.lnk",
        ],
        "exclude_folders": ["00快捷方式", "资料"],
        "monitor_paused": False,
        "rules": [
            {
                "name": "投标与结算",
                "keywords": ["投标", "结算", "报价", "标书"],
                "extensions": [".docx", ".pdf", ".xlsx", ".xls"],
                "target": "投标与结算",
            },
            {
                "name": "售后与统计",
                "keywords": ["统计", "技术中控", "售后工作量", "售后"],
                "extensions": [".docx", ".pdf", ".xlsx", ".xls"],
                "target": "售后与统计",
            },
            {
                "name": "开发与需求",
                "keywords": ["需求", "开发", "原型", "PRD", "设计稿"],
                "extensions": [".md", ".docx", ".pdf", ".fig", ".sketch"],
                "target": "开发与需求",
            },
            {
                "name": "合同与协议",
                "keywords": ["合同", "协议", "补充协议", "委托书"],
                "extensions": [".doc", ".docx", ".pdf"],
                "target": "合同与协议",
            },
            {
                "name": "图纸与工程",
                "keywords": ["图纸", "施工图", "竣工图", "消防", "工程"],
                "extensions": [".dwg", ".dxf", ".pdf", ".rvt"],
                "target": "图纸与工程",
            },
            {
                "name": "图片与媒体",
                "keywords": ["图片", "照片", "视频", "截图", "媒体"],
                "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".mp4", ".mov", ".avi", ".mkv", ".wmv"],
                "target": "图片与媒体",
            },
            {
                "name": "压缩包",
                "keywords": ["压缩", "打包", "归档"],
                "extensions": [".zip", ".rar", ".7z", ".tar", ".gz"],
                "target": "压缩包",
            },
        ],
        "shortcut_target": "00快捷方式",
        "default_target": "临时与杂项",
        "smart_classification_enabled": False,
        "confidence_threshold": 0.85,
    }


def load_config() -> dict[str, Any]:
    """加载配置。若文件不存在则返回默认配置；否则 yaml.safe_load 读入，缺失的顶层 key 用默认补全。"""
    path = get_config_path()
    default = get_default_config()
    if not os.path.isfile(path):
        return default.copy()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return default.copy()
    for key, value in default.items():
        if key not in data:
            data[key] = value
    # 规则为空或缺失时用默认规则，避免曾保存过 rules: [] 后一直无规则
    if not data.get("rules"):
        data["rules"] = list(default["rules"])
    return data


def save_config(cfg: dict[str, Any]) -> None:
    """将配置写回 config.yaml（UTF-8）。"""
    path = get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
