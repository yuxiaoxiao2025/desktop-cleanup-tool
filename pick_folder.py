# -*- coding: utf-8 -*-
"""
独立脚本：弹出文件夹选择对话框，将选中路径打印到 stdout。
供设置页「选择文件夹」按钮调用（web_server 通过 subprocess 执行）。
"""
import os
import sys

def main() -> None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        sys.exit(1)
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    initial = os.path.expanduser("~")
    if len(sys.argv) > 1 and sys.argv[1].strip():
        initial = sys.argv[1].strip()
    path = filedialog.askdirectory(title="选择桌面路径", initialdir=initial)
    if path:
        print(path)
    root.destroy()


if __name__ == "__main__":
    main()
