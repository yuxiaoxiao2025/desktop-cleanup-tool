# -*- coding: utf-8 -*-
"""
Flask Web 服务：历史页 /history，打开路径 /open。
"""
import subprocess
from urllib.parse import unquote

from flask import Flask, redirect, render_template, request

import history_log

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


@app.route("/history")
def history_page():
    """读全部历史（倒序），渲染 history.html。"""
    entries = history_log.get_all()
    return render_template("history.html", entries=entries)


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
