# 桌面整理小工具 Implementation Plan

> **For Claude:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现常驻托盘的桌面整理小工具：监控桌面、延迟时间后按 YAML 规则自动移动文件/文件夹，持久化待整理与历史，托盘菜单与设置/历史 Web 页。

**Architecture:** Python 单进程：主线程启动托盘 (pystray) + 后台线程定时扫描桌面与处理待整理列表 + 轻量 HTTP 服务提供 /settings 与 /history；配置与待整理/历史存于 %APPDATA%\DesktopCleanup\。

**Tech Stack:** Python 3.10+, pystray, PyYAML, Flask, watchdog（或定时轮询）, winotify/plyer（Windows 通知）, shutil

**Spec:** `docs/superpowers/specs/2026-03-14-desktop-cleanup-tool-design.md`

---

## 审查说明（2026-03-14）

对照设计文档对计划做了逐项核对，并已直接修正计划中的以下内容：

| 项 | 问题 | 修正 |
|----|------|------|
| 移动目标路径 | process_due 中若把「目标目录」当 dest_path 直接 move，会把文件误移成“替换目录”。设计要求移入目标目录下并保留原名。 | 明确：`dest_dir = join(desktop_path, target)`，`dest_path = join(dest_dir, name)`，执行 `shutil.move(src_path, dest_path)`。 |
| 数据目录来源 | pending/history_log 需数据目录，设计未在 config 字典里规定 data_dir。 | 约定：config 模块提供 `get_data_dir()`，pending 与 history_log 通过其获取数据目录（不依赖 config 字典）。 |
| 规则匹配-文件夹 | 设计 3.3 对「文件或文件夹名」匹配，文件夹无扩展名。 | 在 rules.py 说明中补充：文件夹无扩展名，仅按 keywords 匹配。 |
| 重试失败项通知 | 设计 4.6 要求 retry_count ≥ 3 时发通知。 | retry_failed 失败分支改为：increment_retry 后若 retry_count ≥ 3 则 notify_in_use。 |
| append_history 参数 | 设计 6.1 与点击跳转需「移动后完整路径」。 | append_history 增加参数 `moved_path`，并在 Task 7 中写出传入 `dest_path`。 |
| 创建目录命令 | 计划中 `mkdir -p` 在 Windows PowerShell 下不适用。 | 补充 Windows 使用 `New-Item -ItemType Directory -Force`。 |

未改动的核对结论：监控/排除/持久化/托盘/历史/设置/学习/单实例与设计一致；run_loop 与 pending 启动校验、tooltip、菜单项与设计一致。

---

## File Structure

| 路径 | 职责 |
|------|------|
| `desktop-cleanup-tool/main.py` | 入口：单实例检查、启动托盘/HTTP/监控循环 |
| `desktop-cleanup-tool/config.py` | 读写 config.yaml、内置默认配置、数据目录路径 |
| `desktop-cleanup-tool/rules.py` | 规则匹配：根据名称/扩展名返回目标相对路径 |
| `desktop-cleanup-tool/pending.py` | 读写 pending.json，增删改待整理项、retry_count |
| `desktop-cleanup-tool/history_log.py` | 追加 history.json、取最近 N 条 |
| `desktop-cleanup-tool/notify.py` | Windows 系统通知（移动成功、占用提示） |
| `desktop-cleanup-tool/monitor.py` | 扫描桌面、更新待整理列表、处理到期项（移动+历史+通知+占用重试） |
| `desktop-cleanup-tool/tray.py` | 托盘图标与右键菜单（历史 10 条、更多、重试、暂停、设置、学习、退出） |
| `desktop-cleanup-tool/web_server.py` | Flask 应用：/settings、/history，与 tray 共享端口 |
| `desktop-cleanup-tool/templates/settings.html` | 设置页：延迟时间、排除、白名单、规则表、监控暂停 |
| `desktop-cleanup-tool/templates/history.html` | 全部历史页：列表+点击跳转 |
| `desktop-cleanup-tool/requirements.txt` | 依赖 |
| `desktop-cleanup-tool/README.md` | 使用说明与运行方式 |

项目根目录建议：`d:\Desktop\desktop-cleanup-tool`（或你指定的目录）。

---

## Chunk 1: 项目骨架与配置层

### Task 1: 项目骨架

**Files:**
- Create: `desktop-cleanup-tool/requirements.txt`
- Create: `desktop-cleanup-tool/README.md`
- Create: `desktop-cleanup-tool/.gitignore`

- [ ] **Step 1: 创建目录与 requirements.txt**

Windows PowerShell: `New-Item -ItemType Directory -Force -Path desktop-cleanup-tool`。Git Bash / Linux: `mkdir -p desktop-cleanup-tool`。

`requirements.txt` 内容：

```
pystray>=0.19.0
Pillow>=9.0.0
PyYAML>=6.0
Flask>=2.3.0
watchdog>=3.0.0
winotify>=1.1.0
```

- [ ] **Step 2: 创建 .gitignore**

```
__pycache__/
*.pyc
.venv/
venv/
*.egg-info/
dist/
build/
```

- [ ] **Step 3: 创建 README.md（简要说明）**

说明：运行 `python main.py`，首次运行会在 %APPDATA%\DesktopCleanup 生成 config.yaml；可从托盘「从桌面学习」更新白名单与目标结构。

- [ ] **Step 4: Commit**

```bash
git add desktop-cleanup-tool/
git commit -m "chore: 桌面整理小工具项目骨架与依赖"
```

---

### Task 2: config.py — 数据目录与 YAML 读写

**Files:**
- Create: `desktop-cleanup-tool/config.py`
- Test: `desktop-cleanup-tool/tests/test_config.py`（可选，或后续补）

- [ ] **Step 1: 实现 config.py**

- 数据目录：`os.path.join(os.environ.get("APPDATA", ""), "DesktopCleanup")`；不存在则创建。
- `get_data_dir()` → 返回数据目录路径（供 config、pending、history_log 等共用）。
- `get_config_path()` → 数据目录下 `config.yaml`。
- `load_config()` → 若文件不存在则返回 `get_default_config()`；否则 `yaml.safe_load` 读入，缺失的顶层 key 用默认补全。
- `save_config(cfg: dict)` → 写回 `config.yaml`（UTF-8）。
- `get_default_config()` → 返回内置默认 dict：`desktop_path`（当前用户 Desktop）、`delay_hours: 24`、`shortcut_whitelist` 空列表、`exclude_folders: ["00快捷方式", "资料"]`、`monitor_paused: False`、`rules: []`（空列表，默认规则在 Task 3 或单独常量）、`shortcut_target: "00快捷方式"`、`default_target: "临时与杂项"`。

- [ ] **Step 2: Commit**

```bash
git add desktop-cleanup-tool/config.py
git commit -m "feat: 配置加载与保存、数据目录与默认配置"
```

---

### Task 3: 内置默认规则与 rules.py

**Files:**
- Create: `desktop-cleanup-tool/config.py` 中或 `desktop-cleanup-tool/default_rules.py` 中定义默认 rules 列表（与设计文档 3.2 一致）
- Create: `desktop-cleanup-tool/rules.py`

- [ ] **Step 1: 在 config 中提供默认 rules**

在 `get_default_config()` 内或单独模块中定义默认 `rules` 列表（至少包含设计文档中的多条：售后与统计、投标与结算、开发与需求、合同与协议、图纸与工程、图片与媒体、压缩包、等），以及默认 `shortcut_whitelist`（如 Cursor、Kimi、Kiro、纳米AI 等）。

- [ ] **Step 2: 实现 rules.py**

- `resolve_target(name: str, is_lnk: bool, config: dict) -> str`
  - 若 `is_lnk`：若 name 在 `config["shortcut_whitelist"]` 中（或标准化后匹配）则返回 `None`（不移动）；否则返回 `config["shortcut_target"]`。
  - 否则：遍历 `config["rules"]`，若 name 包含任一 keyword 或扩展名在 extensions 中，返回该条 `target`（相对路径）；未命中返回 `config["default_target"]`。
- 扩展名：从 name 取 `os.path.splitext(name)[1]`，与规则中 extensions 比较（大小写可统一为小写）。**文件夹**无扩展名，仅按 keywords 匹配。

- [ ] **Step 3: Commit**

```bash
git add desktop-cleanup-tool/config.py desktop-cleanup-tool/rules.py
git commit -m "feat: 内置默认规则与规则匹配逻辑"
```

---

## Chunk 2: 待整理与历史

### Task 4: pending.py

**Files:**
- Create: `desktop-cleanup-tool/pending.py`

- [ ] **Step 1: 实现 pending.py**

- `get_pending_path(config)` → 使用 `config.get_data_dir()`（见下）或从 config 模块导入 `get_data_dir()`，返回数据目录 + `pending.json`。**约定**：config 模块提供 `get_data_dir()`，pending/history_log 通过它解析数据目录，不依赖 config 字典内的 key。
- `load_pending(config: dict) -> list`：读 JSON，返回列表；文件不存在或空则返回 `[]`。每项为 dict：`path`, `name`, `created_at`, `added_at`, `retry_count`（缺则 0）。
- `save_pending(config: dict, items: list)`：写回 UTF-8 JSON。
- `add_pending(config, path, name, created_at)`：load，若 path 已存在则跳过；否则 append 新项（`added_at` 为当前时间 ISO），save。
- `remove_pending(config, path)`：load，过滤掉 path，save。
- `increment_retry(config, path)`：load，找到 path 对应项，`retry_count += 1`，save。
- `get_retry_count(config, path) -> int`：load，找到 path 返回 retry_count，否则 0。
- 启动时校验：load 后过滤掉 path 不存在的项，save。

- [ ] **Step 2: Commit**

```bash
git add desktop-cleanup-tool/pending.py
git commit -m "feat: 待整理列表持久化与增删改"
```

---

### Task 5: history_log.py

**Files:**
- Create: `desktop-cleanup-tool/history_log.py`

- [ ] **Step 1: 实现 history_log.py**

- `get_history_path(config)` → 使用 config 模块的 `get_data_dir()` 得到数据目录，再拼接 `history.json`。
- `append_history(config, original_name, original_path, target_folder, target_folder_display, moved_path)`：读现有 history（若不存在则 `[]`），append 一条 `{ moved_at: iso now, original_name, original_path?, target_folder, target_folder_display, moved_path }`（moved_path 为移动后文件/文件夹的完整路径，供托盘与 /open 使用），写回。
- `get_recent(config, n=10) -> list`：读 history，按 `moved_at` 倒序，取前 n 条返回。

- [ ] **Step 2: Commit**

```bash
git add desktop-cleanup-tool/history_log.py
git commit -m "feat: 历史记录追加与最近 N 条查询"
```

---

## Chunk 3: 通知与监控

### Task 6: notify.py

**Files:**
- Create: `desktop-cleanup-tool/notify.py`

- [ ] **Step 1: 实现 notify.py**

- `notify_moved(name: str, target_display: str)`：系统通知标题/正文如「桌面整理」「XXX 已移至 XXX 文件夹」。
- `notify_in_use(name: str)`：正文「XXX 因被占用未能自动移动，请关闭占用程序后等待下次自动重试，或在托盘菜单中点击“重试失败项”。」
- 使用 winotify 或 plyer；若运行环境非 Windows 可 try/except 静默跳过。

- [ ] **Step 2: Commit**

```bash
git add desktop-cleanup-tool/notify.py
git commit -m "feat: Windows 系统通知"
```

---

### Task 7: monitor.py — 扫描与移动

**Files:**
- Create: `desktop-cleanup-tool/monitor.py`

- [ ] **Step 1: 实现 monitor 逻辑**

- `scan_desktop(config)`：列出 `config["desktop_path"]` 下第一层项（文件+文件夹），排除 `exclude_folders` 和 `desktop.ini`。对每一项：若路径不在 `load_pending(config)` 的 path 列表中，则取创建时间（fallback 修改时间），调用 `add_pending(config, path, name, created_at)`。
- `process_due(config)`：load_pending，对每项检查 `(now - created_at).total_seconds() >= config["delay_hours"] * 3600`。对到期项：
  - 解析目标：若是 .lnk 用 rules.resolve_target(name, True, config)，否则 resolve_target(name, False, config)。若目标为 None（白名单快捷方式）则从 pending 移除并 return。
  - 目标目录绝对路径：`dest_dir = os.path.join(config["desktop_path"], target)`；若不存在则 `os.makedirs(dest_dir, exist_ok=True)`。**移动目标**：文件或文件夹的最终路径为 `dest_path = os.path.join(dest_dir, name)`（将项移入目标目录下，保持原名）。
  - `shutil.move(src_path, dest_path)`；若抛异常（如 PermissionError/OSError 表示占用），则 `increment_retry(config, path)`，若 `get_retry_count(config, path) >= 3` 则 `notify_in_use(name)`，不 remove_pending。
  - 移动成功：`append_history(..., target_folder=dest_dir, moved_path=dest_path)`，`remove_pending(config, path)`，`notify_moved(name, target_folder_display)`。target_folder_display 可用 target 最后一段或相对路径。

- [ ] **Step 2: Commit**

```bash
git add desktop-cleanup-tool/monitor.py
git commit -m "feat: 桌面扫描与到期移动、占用重试与通知"
```

---

### Task 8: 监控循环与“重试失败项”

**Files:**
- Modify: `desktop-cleanup-tool/monitor.py`

- [ ] **Step 1: 添加 run_loop(config, stop_event)**

- 若 `config.get("monitor_paused")` 为 True，则 sleep 一段时间（如 60s）后继续循环，不执行 scan/process。
- 否则：先对 pending 中已有项做一次“路径存在”校验，删除不存在的 path 并 save；然后 `scan_desktop(config)`；再 `process_due(config)`。
- 循环间隔建议 10 分钟（600s），或可配置；循环条件为 not stop_event.is_set()。

- [ ] **Step 2: 添加 retry_failed(config)**

- 获取 pending 中所有 `retry_count > 0` 的项，对每项再执行一次“解析目标 → move”逻辑（同 process_due 中单条），成功则 remove + history + notify；失败则 increment_retry，若 `get_retry_count(config, path) >= 3` 则 `notify_in_use(name)`（与设计 4.6 一致）。

- [ ] **Step 3: Commit**

```bash
git add desktop-cleanup-tool/monitor.py
git commit -m "feat: 监控循环与重试失败项"
```

---

## Chunk 4: 托盘与 Web

### Task 9: tray.py — 托盘与菜单

**Files:**
- Create: `desktop-cleanup-tool/tray.py`

- [ ] **Step 1: 实现托盘图标与菜单**

- 使用 pystray；图标可用 Pillow 画简单图标或放一张 `icon.png`。
- 左键：无操作（不绑定）。
- 右键菜单：
  - 「历史记录」→ 子菜单：调用 `history_log.get_recent(config, 10)`，每条显示「原名称 → 目标文件夹名」；点击某条：用 `subprocess` 或 `os.startfile` 打开目标文件夹并选中文件（Windows: `explorer /select,"<target_path>"`，target_path 为移动后文件/文件夹的绝对路径，需从 history 中取 target_folder + name 拼出）。
  - 「更多」→ 打开浏览器 `http://127.0.0.1:<port>/history`（port 由 main 传入或从共享变量读）。
  - 「重试失败项」→ 调用 `monitor.retry_failed(config)`。
  - 「暂停监控」/「恢复监控」→ 切换 config["monitor_paused"]，save_config(config)，菜单文案随之切换。
  - 「设置」→ 打开 `http://127.0.0.1:<port>/settings`。
  - 「从桌面学习」→ 调用 learn_from_desktop(config)：扫描桌面一级目录（排除 exclude_folders）得文件夹列表；扫描所有 .lnk 文件名更新 shortcut_whitelist；可选将子文件夹结构作为“目标路径候选”存到 config 或仅用于设置页下拉。写回 save_config。
  - 「退出」→ 设置 stop_event，退出托盘 run。
- Tooltip：根据 monitor_paused、pending 条数拼接，如「桌面整理 - 运行中」「桌面整理 - 已暂停」「桌面整理 - 运行中（3 项待整理）」。

- [ ] **Step 2: Commit**

```bash
git add desktop-cleanup-tool/tray.py
git commit -m "feat: 托盘图标与右键菜单、tooltip 状态"
```

---

### Task 10: web_server.py 与 /history

**Files:**
- Create: `desktop-cleanup-tool/web_server.py`
- Create: `desktop-cleanup-tool/templates/history.html`

- [ ] **Step 1: Flask 应用骨架**

- Flask app；路由 `/history`：读 `history_log` 全部（读文件，倒序），渲染 `history.html`，传入列表。列表每项含：original_name, target_folder_display, target_folder（绝对路径或用于拼出选中路径的字段）, moved_at。
- 前端：表格或列表，每行可点击；点击时请求后端一个接口如 `/open?path=...` 或直接前端用 `file://` 不可行，故后端提供 `/open`，接收 path 参数，用 `subprocess.run(["explorer", "/select", path])` 打开，然后重定向回 /history 或返回 204。
- 若 path 为文件夹，则选中该文件夹；若为文件，则选中该文件。history 中需存移动后的完整路径：target_folder 为目录，移动后文件为 target_folder + original_name，所以后端可拼出 full_path。

- [ ] **Step 2: history.html**

- 简单表格：原名称、目标文件夹、移动时间；每行点击调用 `/open?path=<full_path>`（或表单/JS 跳转）。

- [ ] **Step 3: Commit**

```bash
git add desktop-cleanup-tool/web_server.py desktop-cleanup-tool/templates/history.html
git commit -m "feat: 历史页与点击打开目标路径"
```

---

### Task 11: /settings 页

**Files:**
- Modify: `desktop-cleanup-tool/web_server.py`
- Create: `desktop-cleanup-tool/templates/settings.html`

- [ ] **Step 1: 设置页路由与保存**

- GET `/settings`：load_config()，渲染 settings.html，传入 config（desktop_path, delay_hours, exclude_folders, shortcut_whitelist, shortcut_target, default_target, rules, monitor_paused）。
- POST `/settings`（或同一路由根据 method）：接收表单/JSON，校验 desktop_path 存在、delay_hours 1–168；更新 config，save_config(config)；返回「配置已保存」或重定向回 /settings。
- 表单字段：桌面路径、延迟时间（标注「新文件/文件夹在桌面停留多久后再自动整理（小时）」）、排除文件夹（多行或列表编辑）、快捷方式白名单（多行）、快捷方式默认目标、默认目标、监控暂停（复选框）、规则表（每条：name, keywords, extensions, target；支持增删改）。规则表可用多行输入 keywords（逗号或换行）、extensions（逗号），target 下拉或输入。

- [ ] **Step 2: settings.html**

- 简单表单布局；规则用表格 + 每行编辑/删除按钮 + 一行「新增规则」；保存按钮提交 POST。

- [ ] **Step 3: Commit**

```bash
git add desktop-cleanup-tool/web_server.py desktop-cleanup-tool/templates/settings.html
git commit -m "feat: 设置页与配置保存"
```

---

### Task 12: 从桌面学习接口与设置页按钮

**Files:**
- Modify: `desktop-cleanup-tool/web_server.py`、`desktop-cleanup-tool/config.py` 或 tray.py

- [ ] **Step 1: 从桌面学习逻辑**

- 在 config 或单独模块实现 `learn_from_desktop(config)`：扫描 desktop_path 下第一层目录（排除 exclude_folders），得到文件夹名列表；递归或仅一层子文件夹得到“目标路径候选”列表（相对桌面）；扫描桌面根目录所有 .lnk，用文件名列表覆盖 config["shortcut_whitelist"]。将目标路径候选可存入 config 的 optional 键如 `target_candidates` 供设置页下拉；不自动添加 rules 条目。save_config(config)。

- [ ] **Step 2: 设置页「从桌面学习」按钮**

- 在 settings 页加按钮，POST 到 `/learn`，服务端调用 learn_from_desktop，重定向回 /settings 并提示「已更新目标路径与白名单」。

- [ ] **Step 3: Commit**

```bash
git add desktop-cleanup-tool/
git commit -m "feat: 从桌面学习与设置页入口"
```

---

## Chunk 5: 主入口与单实例

### Task 13: main.py

**Files:**
- Create: `desktop-cleanup-tool/main.py`

- [ ] **Step 1: 单实例**

- 使用 `win32mutex` 或跨平台：锁文件在数据目录下 `desktop-cleanup.lock`，启动时 try 创建独占锁；若失败则打印「已在运行」并 exit。或 Windows 下用 `msvcrt.locking` 锁文件。

- [ ] **Step 2: 启动流程**

- load_config()；若无 config 文件则 get_default_config() 并 save（含完整默认 rules），可选弹一次「是否从桌面学习」或首次直接调用 learn_from_desktop 一次。
- 启动 HTTP 服务在后台线程（Flask app.run(port=port, use_reloader=False)），port 固定如 57682 或从 config 读。
- 启动监控循环在另一后台线程（monitor.run_loop(config, stop_event)）。
- 主线程运行 tray：传入 config 引用、port、stop_event；tray 里菜单需要最新 config，可从 config 模块 reload 或传 getter。
- 退出时 stop_event.set()，等待线程结束，释放锁。

- [ ] **Step 3: 待整理列表启动校验**

- 在 monitor.run_loop 第一次迭代或 main 启动时，调用 pending.load_pending，过滤掉 path 不存在的项，save_pending。

- [ ] **Step 4: Commit**

```bash
git add desktop-cleanup-tool/main.py
git commit -m "feat: 主入口、单实例与线程启动"
```

---

### Task 14: 历史记录“打开并选中”与 pending 路径校验

**Files:**
- Modify: `desktop-cleanup-tool/history_log.py`、`desktop-cleanup-tool/monitor.py`

- [ ] **Step 1: 历史条目存移动后完整路径**

- append_history 时增加字段 `moved_path`：移动后的文件或文件夹的完整路径（target_folder + name），便于 /open 直接使用。

- [ ] **Step 2: 托盘「历史记录」点击**

- 托盘子菜单点击某条时，用 history 中该条的 moved_path（或 target_folder + original_name）调用 explorer /select。

- [ ] **Step 3: Commit**

```bash
git add desktop-cleanup-tool/history_log.py desktop-cleanup-tool/tray.py
git commit -m "fix: 历史存移动后路径、托盘与更多页点击跳转"
```

---

### Task 15: 文档与可选打包

**Files:**
- Modify: `desktop-cleanup-tool/README.md`
- Create: `desktop-cleanup-tool/README.md` 中增加运行说明、配置说明、托盘菜单说明

- [ ] **Step 1: 完善 README**

- 安装依赖、运行 `python main.py`、数据目录位置、首次学习、设置页与历史页 URL、延迟时间含义、重试失败项与占用提示。

- [ ] **Step 2: 可选 PyInstaller**

- 若需要单 exe：`pyinstaller --onefile --windowed main.py`（或 --noconsole 避免黑窗），将 icon、templates 等数据文件打包进去或放到同目录。可在计划中记为可选步骤，不强制。

- [ ] **Step 3: Commit**

```bash
git add desktop-cleanup-tool/README.md
git commit -m "docs: 使用说明与运行方式"
```

---

## Execution Handoff

- **Spec:** `docs/superpowers/specs/2026-03-14-desktop-cleanup-tool-design.md`
- **Plan:** `docs/superpowers/plans/2026-03-14-desktop-cleanup-tool.md`
- **项目目录:** 在 `d:\Desktop` 下创建 `desktop-cleanup-tool` 并在此计划中的路径均相对于该目录。

建议：实现前先做一次会话压缩，在新窗口中执行计划效果更好。

执行时请说：

**「执行计划 `docs/superpowers/plans/2026-03-14-desktop-cleanup-tool.md`，使用 subagent-driven-development。」**

若无法使用 subagent，可在当前会话中按 Task 1 → Task 15 顺序逐步实现并勾选步骤。
