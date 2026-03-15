# 智能分类与学习 — 实现审查报告

**审查依据：**  
- 计划：`docs/plans/2026-03-15-smart-rules-and-learning.md`  
- 设计：`docs/superpowers/specs/2026-03-15-smart-rules-and-learning-design.md`  
- API 参考：`docs/qwen/向量化模型的详细使用说明.md`  

**审查范围：** `e:\trae\desktop-cleanup-tool\.worktrees\smart-rules` 分支 `feature/smart-rules-and-learning` 已实现内容（Task 1–8、10–11；Task 9 未实现）。

---

## 一、与计划文档的符合性

### 1. 阶段 1：反馈库存储

| 计划要求 | 实现情况 |
|----------|----------|
| Task 1：`get_feedback_path()` 返回数据目录下 feedback.json | ✅ `feedback_store.py` 实现一致，测试覆盖路径与数据目录 |
| Task 2：单条结构含 file_name, extension, target, original_path, timestamp, content_summary（可选） | ✅ `add_feedback` 写入上述字段，`content_summary` 首版可空 |
| Task 2：`lookup_feedback(config, file_name, extension)` 取最近一条 | ✅ `reversed(items)` 按同名+同扩展名取最后一条 |
| Task 2：计划约定首版按 (file_name, extension)，不含 dir_path | ✅ 与计划一致；扩展「同路径+同名」见计划 Task 2 备注 |
| Task 3：`get_feedback_grouped_by_target(config)` 按 target 分组返回 dict[str, list] | ✅ 实现与计划一致 |

### 2. 阶段 2：智能解析目标

| 计划要求 | 实现情况 |
|----------|----------|
| Task 4：`smart_classification_enabled: False`, `confidence_threshold: 0.85`；load_config 默认补全 | ✅ `get_default_config()` 含两项；`load_config()` 用 `default.items()` 补全缺失 key |
| Task 5：`classify_target_candidates(item_text, extensions, target_folders)`；text-embedding-v4, dimension=1024；无 Key/异常返回 (None, 0.0) | ✅ 与计划及 qwen 文档「文本分类」示例一致；依赖 dashscope、numpy 已入 requirements.txt |
| Task 6：`resolve_target_with_feedback(name, is_lnk, config)` 顺序：规则 → 反馈 → 向量 → default | ✅ 顺序正确；规则非 None 返回 (target, 1.0, "rules")；反馈命中 (target, 1.0, "feedback")；向量命中 (target, score, "vector")；否则 (default_target, 0.0, "default") |
| Task 6：快捷方式白名单（规则返回 None）时调用方不移动 | ✅ 在规则为 None 且 is_lnk 时返回 (None, 0.0, "whitelist")，避免误走 default 移动 |

### 3. 阶段 3：立即整理与反馈回写

| 计划要求 | 实现情况 |
|----------|----------|
| Task 7：smart_classification_enabled 时用 resolve_target_with_feedback，否则 rules.resolve_target | ✅ `_try_move_item` 分支正确 |
| Task 7：target 为 None 则 remove_pending 并 return | ✅ 已实现 |
| Task 7：confidence < threshold 时不移动、不写反馈、不删 pending，仅加入需用户确认列表 | ✅ 调用 `add_to_pending_confirm` 并 return False |
| Task 7：organize_now 在遍历 pending 前先调用 scan_desktop(config) | ✅ 首行即 `scan_desktop(config)` |
| Task 7：移动成功后对 source 为 vector/feedback（至少）写 add_feedback | ✅ 对 source in ("vector","feedback") 或 "rules" 均调用 add_feedback |
| Task 8：需确认列表含 path, name, suggested_target, confidence；GET 列表、POST 确认后执行移动并 add_feedback | ✅ `pending_confirm.py` 与 GET/POST API 符合；confirm 流程：移动、append_history、remove_pending、add_feedback、从列表移除 |

### 4. 阶段 5：从反馈提炼规则建议

| 计划要求 | 实现情况 |
|----------|----------|
| Task 10：`suggest_rules_from_feedback(config)` 按 target 聚合，启发式提炼 keywords/extensions，返回 list[dict] 含 name, keywords, extensions, target；不写 config | ✅ `rule_suggestions.py` 与计划一致 |
| Task 11：GET /api/rule-suggestions 返回建议；POST /api/rule-suggestions/apply 合并进 config["rules"] 并 save_config | ✅ 已实现；合并时按 (target, keywords, extensions) 去重，格式与现有 rules 一致 |

---

## 二、与设计文档的符合性

| 设计条款 | 审查结论 |
|----------|----------|
| **二、立即整理流程**：规则优先 → 反馈/模型兜底；置信度不足进待确认，确认后再移动并写反馈 | 实现与设计一致；低置信度仅入待确认，确认接口执行移动并写反馈 |
| **二、扫描与列表**：立即整理可先执行一次扫描 | organize_now 先 scan_desktop，符合 |
| **七、数据与存储**：反馈库字段含原始路径/文件名、扩展名、可选内容摘要、采纳目标、时间戳 | 单条含 file_name, extension, target, original_path, timestamp, content_summary，符合 |
| **八、与现有行为**：设置页保留规则表格逐条编辑；规则建议为批量采纳，不替代逐条编辑 | Task 11 仅新增规则建议区块与 apply 接口，未改动现有规则表单逻辑，符合 |

---

## 三、与 Qwen/向量文档的符合性

| 文档要求 | 实现情况 |
|----------|----------|
| 零样本分类：`input=[text] + labels`，`dimension=1024`，余弦相似度取最高标签 | `classify_target_candidates` 使用 `input=[item_text] + target_folders`、`dimension=1024`，余弦相似度与文档示例一致 |
| 模型 `text-embedding-v4` | 已使用 |
| API Key 通过环境变量配置（文档说明） | 未在代码中显式读取；依赖 dashscope SDK 默认行为，与文档「配置到环境变量」一致 |

---

## 四、发现的问题与建议

### 1. 重要（建议修复）

- **DashScope 响应与错误处理**  
  **位置：** `smart_resolve.py`，`classify_target_candidates`  
  **问题：** 当前仅用 `resp.output.get("embeddings")` 及长度校验，未检查 `resp.status_code`。若 DashScope 在 API Key 无效或限流等情况下返回 4xx/5xx 且不抛异常，可能误把错误响应当成功使用。  
  **建议：** 查阅 dashscope Python SDK 行为；若错误时仍返回对象且带 `status_code`，在解析前增加 `status_code == 200`（或等效）判断，非成功时返回 `(None, 0.0)`。

### 2. 可选/后续

- **反馈库 lookup 扩展**  
  设计二与计划审查表约定：首版按 (file_name, extension)；若需「同路径+同名」精确匹配，可在后续增加 `lookup_feedback(..., original_path=None)` 并在有 path 时优先匹配 path+name+ext。当前实现与计划一致，无必须修改。

- **Task 9 未实现**  
  会话内一致性 hint（session_history、get_recent_targets_for_extension、hint 拼入向量分支）未做，计划标为可选，审查不要求本次实现。

- **规则建议 apply 的 rules 顺序**  
  当前为「现有 rules 在前 + 新规则按提交顺序追加」。若产品希望「新规则插在特定位置」或「按 target 分组展示」，可在后续在 API 或前端约定顺序策略。

---

## 五、结论

- **与计划：** 已实现的 Task 1–8、10–11 与计划文档一致；Task 6 白名单分支、Task 7 置信度与扫描顺序、Task 8 确认流程与计划及设计一致。
- **与设计：** 流程、数据存储、与现有行为关系符合设计说明。
- **与 Qwen 文档：** 向量模型用法、参数与零样本分类示例一致；建议补强 DashScope 响应与错误处理（见四.1）。

审查完成后，建议优先处理「四、1」中的 status_code/错误处理，其余为可选或后续迭代。
