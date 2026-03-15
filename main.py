# -*- coding: utf-8 -*-
"""
主入口：单实例锁、加载配置、启动 HTTP / 监控 / 托盘，退出时清理。
"""
import os
import socket
import sys
import threading

import config
from monitor import run_loop
from pending import validate_pending
from tray import learn_from_desktop, run_tray
from web_server import app

# Windows 单实例锁
_LOCK_FILE = None


def _acquire_lock() -> bool:
    """在数据目录下创建锁文件并加独占锁；失败返回 False（已在运行）。"""
    global _LOCK_FILE
    data_dir = config.get_data_dir()
    lock_path = os.path.join(data_dir, "desktop-cleanup.lock")
    try:
        _LOCK_FILE = open(lock_path, "w", encoding="utf-8")
    except OSError:
        return False
    try:
        import msvcrt
        msvcrt.locking(_LOCK_FILE.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        _LOCK_FILE.close()
        _LOCK_FILE = None
        return False
    return True


def _ensure_port_usable(port: int) -> int:
    """
    检测端口是否可绑定（避免 Windows 保留端口导致 WSAEACCES）。
    若不可用则返回备用端口 57600。
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
        return port
    except OSError:
        return 57600


def _release_lock() -> None:
    """释放锁并关闭锁文件。"""
    global _LOCK_FILE
    if _LOCK_FILE is None:
        return
    try:
        import msvcrt
        msvcrt.locking(_LOCK_FILE.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    try:
        _LOCK_FILE.close()
    except OSError:
        pass
    _LOCK_FILE = None


def main() -> None:
    if not _acquire_lock():
        print("已在运行")
        sys.exit(1)

    cfg = config.load_config()
    config_path = config.get_config_path()
    if not os.path.isfile(config_path):
        config.save_config(cfg)
        learn_from_desktop(cfg)

    validate_pending(cfg)

    stop_event = threading.Event()
    requested_port = cfg.get("port", 57600)
    port = _ensure_port_usable(requested_port)
    if port != requested_port:
        cfg["port"] = port
        config.save_config(cfg)
    config_ref = [cfg]
    app.config["LIVE_CONFIG_REF"] = config_ref

    def run_http() -> None:
        app.run(host="127.0.0.1", port=port, use_reloader=False)

    http_thread = threading.Thread(target=run_http, daemon=True)
    http_thread.start()

    monitor_thread = threading.Thread(target=run_loop, args=(cfg, stop_event), daemon=False)
    monitor_thread.start()

    run_tray(config_ref, port, stop_event)

    stop_event.set()
    monitor_thread.join(timeout=10.0)
    _release_lock()


if __name__ == "__main__":
    main()
