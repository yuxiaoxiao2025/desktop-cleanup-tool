# 智能分类与学习 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有「规则优先 + 延迟整理」基础上，增加分类缓存/反馈库、规则未命中时用 Qwen 向量做目标推荐、置信度不足时需用户确认并将采纳结果写入反馈库，以及从反馈中批量生成规则建议供用户一次性审核。

**Architecture:** 保持现有 resolve_target → 移动流程；在解析目标前插入「反馈库查询」与可选的「向量分类」层；反馈库用 JSON 存于 %APPDATA%\DesktopCleanup（与 pending/history 一致）；向量用 docs/qwen 的 text-embedding-v4 + 零样本分类（当前项 vs 目标文件夹名列表）得到推荐与置信度；用户确认或自动采纳后写反馈；规则批量更新由「从反馈提炼规则候选」与可选「模型建议整批规则」触发，用户一次性审核后写回 config.yaml。

**Tech Stack:** Python 3.10+，现有栈（config/pending/rules/monitor）；DashScope TextEmbedding（text-embedding-v4，dimension=1024）与可选 Generation（qwen-plus/turbo）；依赖 dashscope（及 numpy 用于余弦相似度），API Key 来自环境变量 DASHSCOPE_API_KEY。

**Spec:** `docs/superpowers/specs/2026-03-15-smart-rules-and-learning.md`  
**API 参考:** `docs/qwen/向量化模型的详细使用说明.md`（零样本分类示例）、`docs/qwen/qwen3的DashScope API 参考.md`、`docs/qwen/qwen3的结构化输出.md`

---

## 审查说明（对照设计文档 2026-03-15）

以下为根据 `docs/superpowers/specs/2026-03-15-smart-rules-and-learning-design.md` 对计划的逐项审查结论与已采纳修正。

| 设计条款 | 审查结论 | 计划侧修正/约定 |
|----------|----------|------------------|
| **二、解析目标**：未命中规则时查「分类缓存/反馈库」，key 为「该文件或同路径+同名」；附录 B.4 反馈库 key 可为 (dir_path, file_name, file_type) 或 (文件名, 扩展名) | 首版反馈库 lookup 仅用 (file_name, extension)，未含 dir_path。若同一文件名在不同目录有不同采纳目标则无法区分。 | 计划约定：Task 2 单条结构保留 `original_path`；`lookup_feedback` 首版按 (file_name, extension) 取最近一条。若需「同路径+同名」精确匹配，在 Task 2 或后续任务中增加 `lookup_feedback(..., original_path=None)`，有 path 时优先匹配 path+name+ext。 |
| **七、数据与存储**：反馈库字段至少包含原始路径/文件名、扩展名、**可选内容摘要**、用户采纳的目标路径、时间戳 | 计划 Task 2 单条结构未列「内容摘要」。 | 在 Task 2 实现说明中注明：单条结构预留 `content_summary`（可选，首版可空），与设计七一致，便于后续多模态/LLM 摘要扩展。 |
| **二、置信度不足**：该条进入「需用户确认」列表，展示「文件名 → 推荐目标」，用户确认或修改后再执行步骤 3 并将**最终采纳的目标**写入反馈库 | 计划 Task 7 曾写「低于阈值时使用 default_target 移动并写反馈」作为临时方案，与设计「先进待确认、确认后再移动并写反馈」冲突。 | 已统一：置信度 &lt; threshold 时**不移动、不写反馈、不删 pending**，仅将该条加入需用户确认列表；移动与写反馈仅在用户确认（或 Task 8 确认接口）后执行。 |
| **二、扫描与列表**：立即整理时「可先执行一次扫描，把当前桌面上符合条件的新项加入列表」 | 计划 Task 7 未明确 organize_now 是否在本次先调用扫描。 | 约定：在 Task 7 实现中，`organize_now` 在遍历 pending 前先调用 `scan_desktop(config)`，与设计「本次若勾选立即整理可先执行一次扫描」一致。 |
| **六、两种规则改进方式**：(1) 由反馈自动提炼 (2) 由模型建议整批规则，两者可并存 | 计划仅包含 (1) 的 Task 10/11，(2) 无对应任务。 | 计划不删减 (1)；在阶段 5 末尾增加说明：「由模型建议整批规则」列为后续迭代（输入当前 rules + 反馈库，调用 Generation 输出建议规则列表，用户一次性审核），或增加可选 Task 12 占位。 |
| **八、与现有行为**：设置页保留现有规则表格的**逐条编辑**能力 | 计划 Task 11 只写「合并进 config」，未提现有逐条编辑。 | 无冲突：Task 11 仅新增「规则建议」的批量采纳接口，不修改现有规则表格的逐条编辑 UI 与逻辑。 |
| Task 6 测试代码 | 测试中 `resolve_target_with_feedback(..., config, None)` 为四参数，与实现签名三参数不一致。 | 测试改为三参数调用，去掉末尾 `None`。 |

**已按上表在计划正文中完成的修正：** 见下方 Task 6（测试调用）、Task 7（置信度不足行为 + organize_now 先扫描）、Task 2（反馈库字段预留 content_summary）、阶段 5 后（模型建议整批规则为后续/可选任务）。

---

## 阶段 1：反馈库存储

### Task 1: 反馈库模块 — 路径与读写

**Files:**
- Create: `feedback_store.py`
- Create: `tests/test_feedback_store.py`

**Step 1: 写失败测试**

在 `tests/test_feedback_store.py` 中：

```python
# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

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
```

**Step 2: 运行测试确认失败**

Run: `cd e:\trae\desktop-cleanup-tool && .venv\Scripts\activate && python -m pytest tests/test_feedback_store.py -v`  
Expected: FAIL (ModuleNotFoundError: No module named 'feedback_store' 或 get_feedback_path 未定义).

**Step 3: 最小实现**

在 `feedback_store.py` 中实现：

```python
# -*- coding: utf-8 -*-
"""反馈库：用户采纳的分类目标持久化，供缓存与规则提炼。"""
import os
from config import get_data_dir

def get_feedback_path() -> str:
    """返回数据目录下的 feedback.json 路径。"""
    return os.path.join(get_data_dir(), "feedback.json")
```

**Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_feedback_store.py -v`  
Expected: PASS.

**Step 5: 提交**

```bash
git add feedback_store.py tests/test_feedback_store.py
git commit -m "feat: 反馈库路径 get_feedback_path 与基础测试"
```

---

### Task 2: 反馈库 — 单条添加与按 key 查询

**Files:**
- Modify: `feedback_store.py`
- Modify: `tests/test_feedback_store.py`

**Step 1: 写失败测试**

在 `tests/test_feedback_store.py` 增加（使用临时目录避免污染真实 APPDATA）：

```python
def test_add_and_lookup_feedback(tmp_path, monkeypatch):
    monkeypatch.setattr("config.get_data_dir", lambda: str(tmp_path))
    from feedback_store import add_feedback, lookup_feedback, get_feedback_path
    add_feedback(None, file_name="报告.pdf", extension=".pdf", target="投标与结算", original_path="C:\\Users\\x\\Desktop\\报告.pdf")
    found = lookup_feedback(None, file_name="报告.pdf", extension=".pdf")
    assert found is not None
    assert found.get("target") == "投标与结算"
```

**Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_feedback_store.py::test_add_and_lookup_feedback -v`  
Expected: FAIL (add_feedback / lookup_feedback 未定义或行为不符).

**Step 3: 最小实现**

约定反馈条目不依赖 config 字典，通过 `get_data_dir()` 定位文件。在 `feedback_store.py` 中：

- 定义单条结构：`file_name`, `extension`, `target`, `original_path`（可选）, `timestamp`（可选）, `content_summary`（可选，设计七要求；首版可空），与附录「缓存/反馈库：表结构与写入时机对照」一致。
- `_load_feedback(config)` 读 `get_feedback_path()` 的 JSON，返回 list；无文件或无效返回 [].
- `_save_feedback(config, items)` 写回 UTF-8.
- `add_feedback(config, file_name, extension, target, original_path="")`：追加一条（含 timestamp）。写入时机与附录一致：移动成功后、或用户确认/修改目标后执行移动时调用。
- `lookup_feedback(config, file_name, extension)`：从 _load_feedback 中查找同名+同扩展名的**最近一条**，返回该条 dict 或 None.

**Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_feedback_store.py -v`  
Expected: PASS.

**Step 5: 提交**

```bash
git add feedback_store.py tests/test_feedback_store.py
git commit -m "feat: 反馈库 add_feedback / lookup_feedback"
```

---

### Task 3: 反馈库 — 按目标路径聚合供规则提炼

**Files:**
- Modify: `feedback_store.py`
- Modify: `tests/test_feedback_store.py`

**Step 1: 写失败测试**

```python
def test_get_feedback_by_target(tmp_path, monkeypatch):
    monkeypatch.setattr("config.get_data_dir", lambda: str(tmp_path))
    from feedback_store import add_feedback, get_feedback_grouped_by_target
    add_feedback(None, "a.pdf", ".pdf", "投标与结算", "")
    add_feedback(None, "b.pdf", ".pdf", "投标与结算", "")
    add_feedback(None, "c.docx", ".docx", "开发与需求", "")
    grouped = get_feedback_grouped_by_target(None)
    assert "投标与结算" in grouped
    assert len(grouped["投标与结算"]) >= 2
    assert "开发与需求" in grouped
```

**Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_feedback_store.py::test_get_feedback_by_target -v`  
Expected: FAIL.

**Step 3: 实现**

`get_feedback_grouped_by_target(config)`：_load_feedback 后按 `target` 分组，返回 `dict[str, list[dict]]`。若后续做 Task 9（会话内一致性），需在 feedback_store 增加 `get_recent_targets_for_extension(config, extension, is_dir, limit)`，按 timestamp DESC、同扩展名与类型过滤，去重后返回最近采纳的 target 列表，供 hint 补足；可在 Task 9 实现时再加。

**Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_feedback_store.py -v`  
Expected: PASS.

**Step 5: 提交**

```bash
git add feedback_store.py tests/test_feedback_store.py
git commit -m "feat: 反馈库按目标聚合 get_feedback_grouped_by_target"
```

---

## 阶段 2：智能解析目标（规则 → 反馈 → 向量）

### Task 4: 配置项 — 智能分类开关与置信度阈值

**Files:**
- Modify: `config.py`（在 get_default_config 中增加 `smart_classification_enabled: False`, `confidence_threshold: 0.85`）
- Modify: `tests/test_feedback_store.py` 或新建 `tests/test_config.py`

**Step 1: 写失败测试**

在 `tests/test_config.py`（新建）中：

```python
def test_default_config_has_smart_classification_keys():
    from config import get_default_config
    cfg = get_default_config()
    assert "smart_classification_enabled" in cfg
    assert "confidence_threshold" in cfg
    assert cfg["confidence_threshold"] >= 0 and cfg["confidence_threshold"] <= 1
```

**Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_config.py -v`  
Expected: FAIL (key 缺失).

**Step 3: 实现**

在 `config.py` 的 `get_default_config()` 返回的 dict 中增加：
- `smart_classification_enabled`: False
- `confidence_threshold`: 0.85

并在 `load_config()` 的默认补全中确保这两项存在。

**Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_config.py -v`  
Expected: PASS.

**Step 5: 提交**

```bash
git add config.py tests/test_config.py
git commit -m "feat: 配置项 smart_classification_enabled 与 confidence_threshold"
```

---

### Task 5: 向量分类模块 — 零样本选目标与置信度

**Files:**
- Create: `smart_resolve.py`（仅向量相关函数，不依赖 feedback_store）
- Create: `tests/test_smart_resolve.py`

**Step 1: 写失败测试**

在 `tests/test_smart_resolve.py` 中测试「无 API Key 时返回 None 或明确降级」以及「有 Key 时行为」可先测接口存在：

```python
def test_classify_target_candidates_exists():
    from smart_resolve import classify_target_candidates
    # 无 key 时允许返回 (None, 0.0) 或跳过调用
    result = classify_target_candidates("报告.pdf", [".pdf"], ["投标与结算", "临时与杂项"])
    assert result is not None
    target, score = result
    assert isinstance(score, (int, float))
```

**Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_smart_resolve.py -v`  
Expected: FAIL (函数不存在或签名不符).

**Step 3: 实现**

在 `smart_resolve.py` 中：
- 参考 `docs/qwen/向量化模型的详细使用说明.md` 中「文本分类」示例：`classify_target_candidates(item_text, extensions, target_folders)`。
- 输入：当前项描述文本（如文件名 + 扩展名）、扩展名（用于日志）、目标文件夹名列表（来自 config 的 rules 的 target 去重 + default_target）。
- 使用 `dashscope.TextEmbedding.call(model="text-embedding-v4", input=[item_text] + target_folders, dimension=1024)`，然后对查询向量与各标签向量算余弦相似度，返回 (best_target, best_score)。若无 API Key 或调用异常，返回 (None, 0.0)。
- 依赖：在项目根 requirements.txt 增加 `dashscope` 和 `numpy`（若尚未存在）。

**Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_smart_resolve.py -v`  
Expected: PASS（无 key 时返回 (None, 0.0) 或跳过调用返回合理默认）。

**Step 5: 提交**

```bash
git add smart_resolve.py tests/test_smart_resolve.py requirements.txt
git commit -m "feat: 向量零样本分类 classify_target_candidates"
```

---

### Task 6: 统一解析入口 — 规则 → 反馈 → 向量，返回 (target, confidence, source)

**Files:**
- Create 或 Modify: `smart_resolve.py`（增加 `resolve_target_with_feedback`）
- Modify: `tests/test_smart_resolve.py`

**Step 1: 写失败测试**

```python
def test_resolve_target_with_feedback_rules_first():
    from smart_resolve import resolve_target_with_feedback
    config = {"rules": [{"keywords": ["投标"], "extensions": [".pdf"], "target": "投标与结算"}], "default_target": "临时与杂项"}
    target, confidence, source = resolve_target_with_feedback("投标文件.pdf", False, config)
    assert source == "rules"
    assert target == "投标与结算"
    assert confidence >= 0.99
```

**Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_smart_resolve.py::test_resolve_target_with_feedback_rules_first -v`  
Expected: FAIL.

**Step 3: 实现**

- `resolve_target_with_feedback(name, is_lnk, config)`（内部 import feedback_store）：
  - 先调 `rules.resolve_target(name, is_lnk, config)`；若得到非 None，返回 (target, 1.0, "rules")。
  - 若为 None（或规则未命中）：从 feedback_store 查 `lookup_feedback(config, name, ext)`；若命中返回 (target, 1.0, "feedback")。
  - 若仍未命中且 config 中 `smart_classification_enabled` 为 True：取目标文件夹列表（从 rules 的 target 与 default_target 去重），调 `classify_target_candidates(name + " " + ext, [ext], folder_list)`，得到 (target, score)；若 target 非 None 且 score >= confidence_threshold 返回 (target, score, "vector")，否则返回 (target, score, "vector") 供上层判断需确认。
  - 若仍未命中且未开智能或向量返回 None：返回 (config["default_target"], 0.0, "default")。
- 返回类型：(str | None, float, str)。当 target 为 None（如快捷方式白名单）时，调用方不移动。

**Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_smart_resolve.py -v`  
Expected: PASS.

**Step 5: 提交**

```bash
git add smart_resolve.py tests/test_smart_resolve.py
git commit -m "feat: 统一解析 resolve_target_with_feedback（规则→反馈→向量）"
```

---

## 阶段 3：接入「立即整理」与反馈回写

### Task 7: 立即整理使用智能解析并写反馈

**Files:**
- Modify: `monitor.py`
- Modify: `tests/test_monitor.py`（若不存在则新建最小测试）

**Step 1: 写失败测试**

在 `tests/test_monitor.py` 中（或新建）：
- 测试 `organize_now` 在某一配置下会调用「智能解析」：可用 mock 将 `resolve_target_with_feedback` 替换，检查当返回高置信度时是否执行移动并写反馈。

```python
def test_organize_now_writes_feedback_on_success(monkeypatch, tmp_path):
    from monitor import organize_now
    from config import get_default_config, save_config, get_data_dir
    import feedback_store
    monkeypatch.setattr("config.get_data_dir", lambda: str(tmp_path))
    cfg = get_default_config()
    cfg["desktop_path"] = str(tmp_path)
    save_config(cfg)
    # 添加一条 pending，并 mock 解析结果为 ("投标与结算", 0.9, "vector")
    # 执行 organize_now 后断言 feedback_store 中有对应记录（略，依赖 pending 与 move 的 mock）
```

若测试编写成本高，可改为：仅测试「monitor 从 rules.resolve_target 改为可选的 resolve_target_with_feedback，且移动成功后调用 add_feedback」。

**Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_monitor.py -v`  
Expected: FAIL 或跳过.

**Step 3: 实现**

- 在 `monitor.py` 的 `_try_move_item` 中：若 config 存在且 `smart_classification_enabled` 为 True，则使用 `smart_resolve.resolve_target_with_feedback(name, is_lnk, config)` 得到 (target, confidence, source)；否则沿用 `rules.resolve_target`，得到 target 后视为 (target, 1.0, "rules")。
- 若 target 为 None，逻辑不变（remove_pending 且 return）。
- 若 confidence < config.get("confidence_threshold", 0.85)：**不移动、不写反馈、不删 pending**，将该条加入「需用户确认」列表（Task 8 实现）；与设计一致：置信度不足时只进待确认列表，等用户确认或修改目标后再执行移动并写反馈。
- `organize_now` 在遍历 pending 前先调用 `scan_desktop(config)`，与设计二「本次若勾选立即整理可先执行一次扫描」一致。
- 移动成功后：将**最终采纳的目标**写入反馈库（设计四、二）：若 source 为 "rules" 且希望缓存以便后续反馈提炼也可写，但至少对 source 为 "vector" 或 "feedback" 调用 `feedback_store.add_feedback(config, name, ext, target, original_path=path)`。

**Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_monitor.py tests/test_feedback_store.py tests/test_smart_resolve.py -v`  
Expected: PASS.

**Step 5: 提交**

```bash
git add monitor.py tests/test_monitor.py
git commit -m "feat: 立即整理接入智能解析与反馈回写"
```

---

### Task 8: 需用户确认列表（数据结构与 API）

**Files:**
- Modify: `pending.py` 或新建 `pending_confirm.py`（需确认项列表持久化或仅内存）
- Modify: `web_server.py`（若存在）或预留 API：返回需确认项列表；确认/修改目标后执行移动并写反馈

**Step 1: 写失败测试**

- 测试：当 resolve 返回的 confidence < threshold 时，该项被加入「待确认」列表；确认后执行移动并 add_feedback.

**Step 2–4: 实现与验证**

- 需确认列表可存于内存（list）或单独 JSON（如 `pending_confirm.json`）。结构：每项含 path, name, suggested_target, confidence。
- 设置页或单独接口：GET 待确认列表；POST 确认（指定 path + 最终 target）→ 执行移动、append_history、remove_pending、add_feedback、从待确认列表移除。

**Step 5: 提交**

```bash
git add pending_confirm.py web_server.py tests/
git commit -m "feat: 需用户确认列表与确认接口"
```

---

## 阶段 4：会话内一致性提示（可选）

### Task 9: 单次整理批次内一致性 hint

**Files:**
- Modify: `smart_resolve.py`
- Modify: `monitor.py`

**Step 1: 写失败测试**

- 测试：当同一批次中已对「.pdf」做过分类且写入了 session 缓存时，下一次对另一 pdf 解析时，传入的 hint 列表包含前一次的 target，且 classify 或 resolve 能使用该 hint（例如将 hint 拼入 prompt 或优先返回 hint 中的目标）。

**Step 2–4: 实现与验证**

- 与附录「一致性 hint 格式」对齐：在 `organize_now` 中维护 `session_history: dict[str, list[str]]`，**key 用 signature**：文件为 `"FILE:.pdf"`（扩展名小写），文件夹为 `"DIR:<none>"`；value 为本次已采用的 target 列表，**最多 5 条**（kMaxConsistencyHints）。每次移动成功后，将 target 加入对应 signature 的列表（去重、保持最近 5 条）。
- 收集 hint 时：先取 session_history[signature]；若不足 5 条，从 `feedback_store.get_recent_targets_for_extension(config, extension, is_dir, remaining)` 补足（需在 feedback_store 实现该函数，按 timestamp DESC、同扩展名与类型取最近若干条 target，去重）。
- 调用 `resolve_target_with_feedback` 时传入 `session_hints: list[str]`。在向量分支中，若 hints 非空，将附录中的**固定文案**拼入：`"Recent assignments for similar items:\n" + "\n".join("- " + t for t in hints) + "\nPrefer one of the above when it fits; otherwise, choose the closest consistent alternative."`；再与当前项描述一起参与分类（例如将 hints 中的 target 在目标列表中优先排序或对相似度加权）。

**Step 5: 提交**

```bash
git add smart_resolve.py monitor.py tests/
git commit -m "feat: 单次整理会话内一致性 hint"
```

---

## 阶段 5：从反馈提炼规则建议

### Task 10: 从反馈库生成规则候选

**Files:**
- Create: `rule_suggestions.py`
- Create: `tests/test_rule_suggestions.py`

**Step 1: 写失败测试**

```python
def test_suggest_rules_from_feedback_returns_list():
    from rule_suggestions import suggest_rules_from_feedback
    # 使用临时 feedback 数据
    suggestions = suggest_rules_from_feedback(config_with_tmp_feedback)
    assert isinstance(suggestions, list)
    for s in suggestions:
        assert "target" in s and "keywords" in s or "extensions" in s
```

**Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_rule_suggestions.py -v`  
Expected: FAIL.

**Step 3: 实现**

- `suggest_rules_from_feedback(config)`：调用 `feedback_store.get_feedback_grouped_by_target(config)`，对每个 target 下的文件名/扩展名做启发式提炼：扩展名直接收集；关键词可从文件名中去掉扩展名后分词或按常见分隔符拆分，取频次高的词，组成规则候选 list[dict]，每项含 name（可 target 名）, keywords, extensions, target。
- 返回候选列表，不写 config；写 config 由「用户一次性审核」接口完成。

**Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_rule_suggestions.py -v`  
Expected: PASS.

**Step 5: 提交**

```bash
git add rule_suggestions.py tests/test_rule_suggestions.py
git commit -m "feat: 从反馈提炼规则候选 suggest_rules_from_feedback"
```

---

### Task 11: 设置页「从反馈生成规则建议」与一次性采纳

**Files:**
- Modify: `web_server.py`
- Modify: `templates/settings.html`（或新建「规则建议」子页）

**Step 1: 写失败测试**

- 测试：GET /api/rule-suggestions 返回 suggest_rules_from_feedback 的结果；POST /api/rule-suggestions/apply 接收用户勾选的候选列表，合并进 config["rules"] 并 save_config.

**Step 2–4: 实现与验证**

- 新增 GET /api/rule-suggestions：调用 rule_suggestions.suggest_rules_from_feedback(load_config())，返回 JSON。
- 新增 POST /api/rule-suggestions/apply：body 为 { "rules": [ { name, keywords, extensions, target } ] }，与现有 config["rules"] 合并（去重或追加），save_config，返回 200。

**Step 5: 提交**

```bash
git add web_server.py templates/
git commit -m "feat: 设置页从反馈生成规则建议与一次性采纳"
```

---

### （可选）Task 12: 由模型建议整批规则

设计六第二种方式：「由模型建议整批规则」— 输入当前 rules + 反馈库 (文件名/摘要 → 目标)，输出模型建议的新增/修改规则列表，用户一次性审核后合并。可与 Task 10/11 并存。若实现：新增接口（如 POST /api/rule-suggestions/from-llm）调用 `dashscope.Generation.call`，prompt 含当前 rules 与反馈摘要，要求返回 JSON 规则列表；前端复用或扩展规则建议审核 UI，采纳后合并进 config。列为后续迭代或可选任务。

---

## 附录：与附录 B（zread）及 docs/qwen 对齐的细节点

以下片段直接对齐设计说明附录 B（ai-file-sorter 的 zread 扫库结果）与 `docs/qwen`，实现时可直接复用或对照。对应 zread 重点：**run_llm_with_timeout、build_whitelist_context、build_combined_context** 的 prompt 拼接；**DatabaseManager** 的缓存表结构、key 与写入时机；**ConsistencyPassService** 与「More consistent」的实现（会话内 hint 与可选批次归一）。

### 1. Prompt 与请求（若后续接入 LLM 分类）

- **白名单注入（build_whitelist_context）**：主类别与子类别用编号列表，约束模型「从编号列表中选且仅选一个」；无子类别白名单时写 "any" 并说明不要重复主类别。
```text
Allowed main categories (pick exactly one label from the numbered list):
1) 投标与结算
2) 开发与需求
...
Allowed subcategories (pick exactly one label from the numbered list):
1) 合同
2) 报价
...
# 若无子类别白名单则：
Allowed subcategories: any (pick a specific, relevant subcategory; do not repeat the main category).
```
- **组合上下文顺序（build_combined_context）**：语言说明 → 白名单块（若启用）→ 一致性 hint 块，块之间用 `\n\n` 连接。
- **LLM 超时（run_llm_with_timeout）**：异步调用 + 主线程 wait_for(timeout)；默认本地 60s、远程 10s；可环境变量覆盖（如 `AI_FILE_SORTER_LOCAL_LLM_TIMEOUT` / `AI_FILE_SORTER_REMOTE_LLM_TIMEOUT`）。本计划若后续加 Generation 分类，可同样用环境变量控制超时（如 `DESKTOP_CLEANUP_LLM_TIMEOUT_SECONDS`），参考 `docs/qwen/qwen3的DashScope API 参考.md`。

### 2. 一致性 hint 格式（format_hint_block，Task 9 直接采用）

```text
Recent assignments for similar items:
- <target1>
- <target2>
...
Prefer one of the above when it fits; otherwise, choose the closest consistent alternative.
```
- 本项目为「单目标」无 subcategory，每行即一个目标文件夹名；与 ai-file-sorter 的 `category : subcategory` 形式等价为一行一个 target。
- **Session 签名**：key 用 `make_file_signature(is_dir, extension)` → 文件为 `"FILE:.pdf"`，文件夹为 `"DIR:<none>"`（无扩展名）；value 为本次已采用的 target 列表，**最多 5 条**（kMaxConsistencyHints）。
- **补足来源**：先查当前会话同 signature 的历史；不足 5 条时从反馈库按「同扩展名、同类型」取最近若干条（等价 ai-file-sorter 的 `get_recent_categories_for_extension`），按时间倒序、去重后填入。

### 3. 缓存/反馈库：表结构与写入时机对照

| ai-file-sorter (file_categorization) | 本计划 (feedback.json) |
|--------------------------------------|-------------------------|
| UNIQUE(file_name, file_type, dir_path) | 首版 key 等价 (file_name, extension)；可扩展 original_path 参与 lookup |
| file_name, file_type ("F"/"D"), dir_path, category, subcategory, taxonomy_id, categorization_style, timestamp | file_name, extension, target, original_path, timestamp, content_summary（可选） |
| 写入时机：分类结果写出 + 用户图审修改后写回 + ConsistencyPass 归一后写回 | 写入时机：移动成功后 add_feedback（规则/向量/反馈来源的采纳）；用户确认或修改目标后执行移动并 add_feedback |
| get_recent_categories_for_extension(extension, file_type, limit) 按 timestamp DESC，同 file_type、扩展名匹配，去重 | get_feedback_grouped_by_target 按 target 聚合；按扩展名取近期：在 feedback_store 中新增 `get_recent_targets_for_extension(extension, is_dir, limit)`，按 timestamp DESC 过滤、去重后返回 list[(target)]，供 Task 9 的 session hint 补足 |

实现 Task 3 后，若做 Task 9，需在 `feedback_store` 增加 `get_recent_targets_for_extension(config, extension, is_dir, limit)`，返回最近采纳的 target 列表（用于拼入一致性 hint）。

### 4. ConsistencyPassService 风格「More consistent」批次归一（可选）

- 设计附录 B.4：可选「单次整理完成后对当批推荐做一次一致性后处理或仅做会话内 hint」。
- 若实现「批次后归一」：在单次 organize_now 完成后，对当批已分类项按 chunk（约 10 条）调用 LLM；prompt 要点：taxonomy 归一助手、合并近义标签、保留原意、每行 `<id> => <Category> : <Subcategory>`（本项目可简化为 `<path> => <target>`），最后一行 `END`；已知目标列表以 JSON 注入。响应解析：优先 JSON `harmonized` 数组，否则按行解析至 `END`；解析后写回反馈库并更新内存。参考 `docs/qwen/qwen3的结构化输出.md` 可要求模型直接返回 JSON。
- 本计划阶段 4 仅做「会话内 hint」，不做二次 LLM 批次归一；若需后者可单独加可选任务。

### 5. docs/qwen 引用汇总

| 用途 | 文档与用法 |
|------|------------|
| 向量零样本分类、余弦相似度 | `docs/qwen/向量化模型的详细使用说明.md` — 文本分类示例：TextEmbedding.call(model="text-embedding-v4", input=[text]+labels, dimension=1024)，余弦相似度取最高标签 |
| LLM 分类 / 规则建议 | `docs/qwen/qwen3的DashScope API 参考.md` — Generation.call，messages 含目标列表与当前项 |
| 稳定输出结构 | `docs/qwen/qwen3的结构化输出.md` — response_format 为 json_object / json_schema，便于解析 target 或规则列表 |
| 多模态（后续） | `docs/qwen/多模态融合向量.md`、向量文档中的多模态 embedding，用于文件名+图片/摘要融合 |

---

## 测试与文档

- **全量测试:** `python -m pytest tests/ -v`
- **编码:** 所有新文件 UTF-8；读写文件 encoding="utf-8"；若需 stdout 中文，按项目约定设置 PYTHONIOENCODING 或 sys.stdout.
- **参考:** 设计说明 `docs/superpowers/specs/2026-03-15-smart-rules-and-learning.md` 及其中附录 B；本计划上文「附录：与附录 B（zread）及 docs/qwen 对齐的细节点」；`docs/qwen/向量化模型的详细使用说明.md` 零样本分类与余弦相似度；`docs/qwen/qwen3的DashScope API 参考.md`、`docs/qwen/qwen3的结构化输出.md`。

---

## 执行选择

计划已保存至 `docs/plans/2026-03-15-smart-rules-and-learning.md`。

**两种执行方式：**

1. **Subagent-Driven（本会话）** — 按任务派发子 agent，每任务后审查，迭代快。  
   **必需子技能：** 使用 superpowers:subagent-driven-development。

2. **Parallel Session（新会话）** — 在新会话中打开本计划，用 executing-plans 按检查点批量执行。  
   **必需子技能：** 新会话使用 superpowers:executing-plans。

**请选择一种方式。**
