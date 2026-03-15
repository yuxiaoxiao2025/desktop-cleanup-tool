# -*- coding: utf-8 -*-
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from config import get_default_config
from pending import add_pending, load_pending


def test_organize_now_calls_resolve_target_with_feedback_when_smart_enabled_and_writes_feedback(
    monkeypatch, tmp_path
):
    """
    当 smart_classification_enabled 为 True 时，monitor 使用 resolve_target_with_feedback；
    移动成功后若 source 为 vector/feedback 则调用 add_feedback。
    """
    data_dir = str(tmp_path)
    monkeypatch.setattr("config.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("pending.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("feedback_store.get_data_dir", lambda: data_dir)

    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    test_file = desktop / "报告.pdf"
    test_file.write_text("dummy", encoding="utf-8")

    cfg = get_default_config()
    cfg["desktop_path"] = str(desktop)
    cfg["smart_classification_enabled"] = True
    cfg["confidence_threshold"] = 0.85

    add_pending(cfg, str(test_file), "报告.pdf", datetime.now().isoformat())
    assert len(load_pending(cfg)) == 1

    resolve_calls = []
    add_feedback_calls = []

    def fake_resolve(name, is_lnk, config):
        resolve_calls.append((name, is_lnk, config))
        return ("投标与结算", 0.9, "vector")

    def fake_add_feedback(config, file_name, extension, target, original_path="", content_summary=""):
        add_feedback_calls.append({
            "config": config,
            "file_name": file_name,
            "extension": extension,
            "target": target,
            "original_path": original_path,
        })

    with patch("monitor.smart_resolve.resolve_target_with_feedback", side_effect=fake_resolve), \
         patch("monitor.feedback_store.add_feedback", side_effect=fake_add_feedback):
        from monitor import organize_now
        organize_now(cfg)

    assert len(resolve_calls) == 1
    assert resolve_calls[0][0] == "报告.pdf"
    assert resolve_calls[0][1] is False

    assert len(add_feedback_calls) == 1
    assert add_feedback_calls[0]["file_name"] == "报告.pdf"
    assert add_feedback_calls[0]["extension"] == ".pdf"
    assert add_feedback_calls[0]["target"] == "投标与结算"
    assert add_feedback_calls[0]["original_path"] == str(test_file)

    dest_dir = desktop / "投标与结算"
    assert dest_dir.is_dir()
    assert (dest_dir / "报告.pdf").exists()
    assert not test_file.exists()


def test_organize_now_calls_scan_desktop_before_processing(monkeypatch, tmp_path):
    """organize_now 在遍历 pending 前先调用 scan_desktop。"""
    data_dir = str(tmp_path)
    monkeypatch.setattr("config.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("pending.get_data_dir", lambda: data_dir)

    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    cfg = get_default_config()
    cfg["desktop_path"] = str(desktop)
    cfg["smart_classification_enabled"] = False

    scan_calls = []

    def capture_scan(config):
        scan_calls.append(config)

    with patch("monitor.scan_desktop", side_effect=capture_scan):
        from monitor import organize_now
        organize_now(cfg)

    assert len(scan_calls) == 1
    assert scan_calls[0] is cfg
