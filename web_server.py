# -*- coding: utf-8 -*-
"""
Flask Web 服务：历史页 /history，打开路径 /open，设置页 /settings。
"""
import os
import re
import subprocess
import sys
from urllib.parse import unquote

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for

import config as config_module
import history_log
from pending_confirm import confirm as confirm_pending_item, get_list as get_pending_confirm_list
from tray import learn_from_desktop

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.secret_key = os.urandom(16).hex()


def _sync_live_config(cfg: dict) -> None:
    """将已保存的配置同步到主进程的「活」配置（config_ref），使 monitor/tray 立即生效。"""
    ref = app.config.get("LIVE_CONFIG_REF")
    if ref and len(ref) > 0:
        ref[0].clear()
        ref[0].update(cfg)


def _parse_rules_from_form(form):
    """从 request.form 解析 rules：键为 rules_<i>_name/keywords/extensions/target。"""
    indices = set()
    for key in form:
        m = re.match(r"^rules_(\d+)_name$", key)
        if m:
            indices.add(int(m.group(1)))
    rules = []
    for i in sorted(indices):
        name = (form.get("rules_%d_name" % i) or "").strip()
        if not name:
            continue
        keywords_raw = (form.get("rules_%d_keywords" % i) or "").strip()
        keywords = [
            k.strip()
            for k in re.split(r"[\s,，]+", keywords_raw)
            if k.strip()
        ]
        exts_raw = (form.get("rules_%d_extensions" % i) or "").strip()
        extensions = [
            e.strip() if e.strip().startswith(".") else "." + e.strip()
            for e in re.split(r"[\s,，]+", exts_raw)
            if e.strip()
        ]
        target = (form.get("rules_%d_target" % i) or "").strip() or None
        rules.append({
            "name": name,
            "keywords": keywords,
            "extensions": extensions,
            "target": target or "",
        })
    return rules


@app.route("/favicon.ico")
def favicon():
    """避免浏览器自动请求 /favicon.ico 时返回 404。有 static/favicon.ico 则返回该文件，否则返回 204。"""
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    favicon_path = os.path.join(static_dir, "favicon.ico")
    if os.path.isfile(favicon_path):
        return send_from_directory(static_dir, "favicon.ico")
    return "", 204


@app.route("/api/pick-folder")
def api_pick_folder():
    """弹出文件夹选择对话框，返回选中路径的 JSON。供设置页「选择文件夹」按钮调用。"""
    initial = request.args.get("initialdir", "").strip() or os.path.join(os.path.expanduser("~"), "Desktop")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pick_script = os.path.join(script_dir, "pick_folder.py")
    if not os.path.isfile(pick_script):
        return jsonify({"ok": False, "path": "", "error": "pick_folder.py not found"}), 500
    try:
        r = subprocess.run(
            [sys.executable, pick_script, initial],
            capture_output=True,
            text=True,
            timeout=120,
        )
        path = (r.stdout or "").strip()
        return jsonify({"ok": True, "path": path})
    except (OSError, subprocess.TimeoutExpired) as e:
        return jsonify({"ok": False, "path": "", "error": str(e)}), 500


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    """GET：加载配置并渲染设置页；POST：校验并保存配置，重定向回 /settings 并带成功提示。"""
    if request.method == "GET":
        cfg = config_module.load_config()
        return render_template("settings.html", config=cfg)

    # POST：接收表单，校验并保存
    form = request.form
    desktop_path = (form.get("desktop_path") or "").strip()
    try:
        delay_hours = int(form.get("delay_hours") or "24")
    except ValueError:
        delay_hours = 24
    exclude_raw = (form.get("exclude_folders") or "").strip()
    exclude_folders = [x.strip() for x in exclude_raw.splitlines() if x.strip()]
    whitelist_raw = (form.get("shortcut_whitelist") or "").strip()
    shortcut_whitelist = [x.strip() for x in whitelist_raw.splitlines() if x.strip()]
    shortcut_target = (form.get("shortcut_target") or "").strip()
    default_target = (form.get("default_target") or "").strip()
    monitor_paused = form.get("monitor_paused") == "on"
    rules = _parse_rules_from_form(form)

    errors = []
    if not desktop_path:
        errors.append("请填写桌面路径。")
    elif not os.path.isdir(desktop_path):
        errors.append("桌面路径不存在或不是目录：%s" % desktop_path)
    if delay_hours < 1 or delay_hours > 168:
        errors.append("延迟时间须在 1–168 小时之间。")

    if errors:
        cfg = config_module.load_config()
        cfg["desktop_path"] = desktop_path
        cfg["delay_hours"] = delay_hours
        cfg["exclude_folders"] = exclude_folders
        cfg["shortcut_whitelist"] = shortcut_whitelist
        cfg["shortcut_target"] = shortcut_target
        cfg["default_target"] = default_target
        cfg["monitor_paused"] = monitor_paused
        cfg["rules"] = rules
        cfg["_errors"] = errors
        return render_template("settings.html", config=cfg), 400

    cfg = config_module.load_config()
    cfg["desktop_path"] = desktop_path
    cfg["delay_hours"] = delay_hours
    cfg["exclude_folders"] = exclude_folders
    cfg["shortcut_whitelist"] = shortcut_whitelist
    cfg["shortcut_target"] = shortcut_target
    cfg["default_target"] = default_target
    cfg["monitor_paused"] = monitor_paused
    cfg["rules"] = rules
    config_module.save_config(cfg)
    _sync_live_config(cfg)
    return redirect(url_for("settings_page") + "?saved=1", code=302)


@app.route("/history")
def history_page():
    """读全部历史（倒序），渲染 history.html。"""
    entries = history_log.get_all()
    return render_template("history.html", entries=entries)


@app.route("/learn", methods=["POST"])
def learn_from_desktop_route():
    """从桌面学习：更新 target_candidates 与 shortcut_whitelist，重定向回设置页并提示。"""
    cfg = config_module.load_config()
    learn_from_desktop(cfg)
    _sync_live_config(cfg)
    return redirect(url_for("settings_page") + "?learned=1", code=302)


@app.route("/api/pending-confirm", methods=["GET"])
def api_pending_confirm_list():
    """返回需用户确认项列表 JSON。"""
    items = get_pending_confirm_list()
    return jsonify(items)


@app.route("/api/pending-confirm/confirm", methods=["POST"])
def api_pending_confirm_confirm():
    """
    确认一项：body JSON { "path": "...", "target": "..." }。
    执行移动、写历史、移除 pending、写 feedback、从待确认列表移除。
    """
    if not request.is_json:
        return jsonify({"ok": False, "error": "需要 JSON 请求体"}), 400
    data = request.get_json() or {}
    path = (data.get("path") or "").strip()
    target = (data.get("target") or "").strip()
    if not path or not target:
        return jsonify({"ok": False, "error": "缺少 path 或 target"}), 400
    cfg = config_module.load_config()
    ok, err = confirm_pending_item(cfg, path, target)
    if ok:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": err or "确认失败"}), 400


@app.route("/open")
def open_path():
    """
    接收 path 参数，用 explorer /select 打开并选中该路径，然后重定向回 /history。
    若 path 缺失或无效，仍重定向回 /history。
    """
    path = request.args.get("path")
    if path:
        path = unquote(path).strip()
        if path:
            try:
                subprocess.run(
                    ["explorer", "/select", path],
                    check=False,
                    timeout=5,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
    return redirect("/history", code=302)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
