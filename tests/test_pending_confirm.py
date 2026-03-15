# -*- coding: utf-8 -*-
"""需用户确认列表与 confirm 接口的测试。"""
from datetime import datetime
from unittest.mock import patch

import pytest

from config import get_default_config
from pending import add_pending, load_pending
from history_log import get_all as get_all_history
import feedback_store


def test_low_confidence_adds_to_pending_confirm_list(monkeypatch, tmp_path):
    """
    当 resolve 返回的 confidence < threshold 时，该项被加入待确认列表；
    不移动、不删 pending、不写 feedback。
    """
    data_dir = str(tmp_path)
    monkeypatch.setattr("config.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("pending.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("feedback_store.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("history_log.get_data_dir", lambda: data_dir)

    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    test_file = desktop / "模糊名.pdf"
    test_file.write_text("dummy", encoding="utf-8")

    cfg = get_default_config()
    cfg["desktop_path"] = str(desktop)
    cfg["smart_classification_enabled"] = True
    cfg["confidence_threshold"] = 0.85

    add_pending(cfg, str(test_file), "模糊名.pdf", datetime.now().isoformat())
    assert len(load_pending(cfg)) == 1

    def fake_resolve(name, is_lnk, config):
        return ("建议目标", 0.5, "vector")  # confidence 0.5 < 0.85

    with patch("monitor.smart_resolve.resolve_target_with_feedback", side_effect=fake_resolve):
        import pending_confirm
        pending_confirm._pending_confirm.clear()
        from monitor import organize_now
        organize_now(cfg)

    items = pending_confirm.get_list()
    assert len(items) == 1
    assert items[0]["path"] == str(test_file)
    assert items[0]["name"] == "模糊名.pdf"
    assert items[0]["suggested_target"] == "建议目标"
    assert items[0]["confidence"] == 0.5

    assert test_file.exists()
    assert len(load_pending(cfg)) == 1
    assert len(get_all_history(cfg)) == 0


def test_confirm_moves_file_and_writes_feedback(monkeypatch, tmp_path):
    """
    确认后：执行移动、append_history、remove_pending、add_feedback、从待确认列表移除。
    """
    data_dir = str(tmp_path)
    monkeypatch.setattr("config.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("pending.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("feedback_store.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("history_log.get_data_dir", lambda: data_dir)

    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    test_file = desktop / "报告.pdf"
    test_file.write_text("dummy", encoding="utf-8")

    cfg = get_default_config()
    cfg["desktop_path"] = str(desktop)
    cfg["smart_classification_enabled"] = True

    add_pending(cfg, str(test_file), "报告.pdf", datetime.now().isoformat())

    import pending_confirm
    pending_confirm._pending_confirm.clear()
    pending_confirm.add_to_pending_confirm(
        str(test_file), "报告.pdf", "投标与结算", 0.7
    )
    assert len(pending_confirm.get_list()) == 1

    ok, err = pending_confirm.confirm(cfg, str(test_file), "投标与结算")
    assert ok is True
    assert err is None

    assert not test_file.exists()
    dest_dir = desktop / "投标与结算"
    assert dest_dir.is_dir()
    assert (dest_dir / "报告.pdf").exists()

    history = get_all_history(cfg)
    assert len(history) == 1
    assert history[0]["original_name"] == "报告.pdf"
    assert "投标与结算" in history[0]["target_folder_display"]

    assert len([p for p in load_pending(cfg) if p.get("path") == str(test_file)]) == 0

    # 反馈库应有一条
    fb = feedback_store.lookup_feedback(cfg, "报告.pdf", ".pdf")
    assert fb is not None
    assert fb.get("target") == "投标与结算"

    assert len(pending_confirm.get_list()) == 0
