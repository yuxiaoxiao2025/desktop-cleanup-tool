# 智能分类与学习 — 设计说明

**日期**：2026-03-15  
**状态**：草案  
**前置**：在现有「规则优先 + 延迟整理」基础上，增强分类智能化、减少人工维护规则，并支持「越用越聪明」。

---

## 一、目标与约束

- **B 方案**：多数项自动分类整理，少数由用户确认或微调；不追求零配置，但要减少「一条条改规则」的负担。
- **越用越聪明**：从用户的确认/修正中学习，使同类项后续更易命中正确目标，或自动沉淀为规则。
- **规则不满但不想一条条改**：提供「批量/自动改进规则」能力——由系统从反馈中提炼或由模型建议整批规则，用户一次性审核采纳，而不是逐条编辑。

---

## 二、「立即整理」完整流程（方案落地后）

你点击「立即整理」后，对**待整理列表中的每一项**（包括桌面上新出现的文件/文件夹），会按下面步骤执行；整体仍遵守「规则优先 → 模型兜底 → 需确认时弹窗/列表」。

1. **扫描与列表**  
   与现在一致：待整理列表来自 `pending.json`（已存在项）+ 本次若勾选「立即整理」可先执行一次扫描，把当前桌面上符合条件的新项加入列表。不判断延迟时间，对所有列表项执行后续步骤。

2. **对每一项解析目标**  
   - **先走现有规则**：用 `resolve_target(name, is_lnk, config)`，若命中某条规则的 keywords 或 extensions，得到 `target`（相对路径），**直接采用**，不调模型。  
   - **未命中规则时**：  
     - 查**分类缓存/反馈库**：若该文件或「同路径+同名」曾在缓存中有用户采纳或历史采纳的目标，则优先用缓存结果作为推荐目标。  
     - 若无缓存或希望用模型再判：用 **Qwen 向量或 LLM**（见第五节、附录 A）在「目标文件夹列表」或「类别白名单」中给出一个推荐目标；若存在多候选，可用向量相似度排序或排序模型选出一个，并得到**置信度**。  
   - **置信度足够高**（例如高于阈值）：将该目标视为「自动采纳」，直接进入步骤 3 执行移动。  
   - **置信度不足**或**未配置模型/未启用智能分类**：该条进入「需用户确认」列表（例如在设置页的「待确认项」表格，或弹窗列表），展示「文件名 → 推荐目标」，你可修改目标或选择「移入默认目标」「跳过」等；你确认或修改后，再执行步骤 3，并将**最终采纳的目标**写入反馈库。

3. **执行移动**  
   与现在一致：根据最终目标创建目录、移动文件/文件夹、写历史、从 pending 移除、发通知。若移动失败（如被占用），按现有逻辑重试与通知。

4. **学习与规则更新（后台/按需）**  
   - 每次「用户确认或修改后的目标」会写入**反馈库**（及分类缓存），供后续相似项推荐。  
   - **规则不会在你点击「立即整理」时自动改写**。规则的批量更新发生在：  
     - 你在设置页（或单独入口）点击「从反馈生成规则建议」：系统从反馈库提炼出规则候选，整表展示，你**一次性勾选采纳或微调后采纳**，再保存配置；或  
     - 你使用「由模型建议整批规则」：模型根据当前规则 + 反馈库输出建议，你一次性审核后合并进配置。  
   因此：**「立即整理」只做「解析目标 → 确认（如需）→ 移动」；规则的自动更新是单独动作，由你触发并一次性审核。**

总结：遇到新文件/新文件夹时，点击「立即整理」会先规则匹配，未命中则用缓存或模型推荐；高置信度则直接移，低置信度则让你确认或改目标后再移；你的确认会写入反馈库用于「越用越聪明」，规则本身要等你主动「生成规则建议」并一次性审核后才会改。

---

## 三、参考：GitHub 高星项目思路

以下思路来自对 **ai-file-sorter**（hyperfield，约 598 stars）与 **file_organizer**（mondaychen，约 108 stars）的 README 与源码；README 通过 `raw.githubusercontent.com` 抓取，ai-file-sorter 的 **CategorizationService.hpp** 通过 GitHub API 抓取。

### 3.1 ai-file-sorter 要点

- **不依赖固定规则**：逐步建立对「你通常如何整理与命名」的内部理解，使分类与命名建议随时间更一致；所有建议在应用前均可审阅与调整。
- **分类输入**：文件名、扩展名、文件夹上下文、以及**学习到的整理模式**。
- **分类模式**：
  - **More refined**：更细粒度，适合长尾或混合文件夹。
  - **More consistent**：同一批次内，模型会收到「当前会话内已有分类」的一致性提示，使相似文件名/扩展名倾向同一类别。
- **类别白名单（Category whitelists）**：可维护多份命名白名单（约 15–20 个类别/子类别），在会话中勾选「使用白名单」后，将白名单注入 LLM 的 prompt，约束输出词汇；与「More consistent」搭配可得到更强一致性。
- **分类缓存数据库（SQLite）**：按「目录路径 + 文件名 + 文件类型」存分类结果、建议新文件名、是否已重命名等；用户在图审中改名或移动后，缓存会更新；下次运行可跳过已处理项并保持建议一致。
- **多模态**：图片用 LLaVA 等视觉模型做描述与命名建议；文档用同一 LLM 做摘要与命名建议；音视频用元数据生成规范文件名。

### 3.2 file_organizer 要点

- **目标目录由 LLM 决定**：根据文件名、类型与内容，由 LLM（如 GPT/Claude）直接给出目标目录。

### 3.3 对本项目的启示

- 用「目标文件夹列表 + 可选白名单/描述」作为 LLM/向量的约束，而不是仅靠手写 keywords/extensions。
- 用**会话内或持久化缓存**记录「文件名/路径 → 目标」的映射，实现一致性并减少重复调用。
- 用户修正要**回写缓存/反馈库**，用于后续相似项推荐或规则提炼。
- 规则可**由系统从反馈中批量生成或更新**，用户只做一次性审核，避免「一条条改」。

### 3.4 ai-file-sorter 源码要点（CategorizationService）

通过 GitHub API 与 `raw.githubusercontent.com` 抓取 **app/include/CategorizationService.hpp** 得到的实现要点（若你用 **zread** 扫仓库，可在此基础上继续看具体 prompt 拼接与 DB 表结构）：

- **分类流程**：`categorize_entries` → 对每条 `categorize_single_entry`；内部先 `try_cached_categorization`，若无缓存再 `categorize_with_cache` → `run_categorization_with_cache` → 调 `categorize_via_llm`（`run_llm_with_timeout`）得到原始响应，校验后写入 DB 并更新**会话内一致性历史**。
- **Prompt 组成**：`build_combined_context(hint_block)` 中组合了**语言说明**、**白名单**（`build_whitelist_context()`）和**一致性提示**（`hint_block`）。一致性提示来自 `collect_consistency_hints(signature, session_history, extension, file_type)`，即当前会话内同类型/同扩展名已分类结果，供「More consistent」模式使用。
- **缓存**：由 `DatabaseManager` 管理；以目录路径 + 文件名 + 文件类型为 key，存解析后的 category/subcategory、建议新文件名等；用户在图审中修改后写回缓存。
- **与本节设计的对应**：我们的「规则优先 → 缓存/模型兜底 → 用户确认后写反馈」与之类似；可借鉴「会话内一致性提示」在单次「立即整理」批次内对相似文件给出一致目标。

---

## 四、整体架构（规则优先 + 模型兜底 + 学习）

- **第一层：现有规则**  
  继续用 `rules`（keywords + extensions）按顺序匹配；命中则直接得到目标，不调用模型。

- **第二层：模型兜底**  
  未命中规则时，用「Qwen 多模态 + 向量 + 排序」给出推荐目标（见下节）。

- **第三层：用户确认与微调**  
  对模型推荐可接受则确认执行；可修改目标后再执行；所有「最终采纳的目标」写入反馈库。

- **学习与规则批量改进**  
  - **反馈库**：持久化「(文件名、扩展名、可选内容摘要) → 用户采纳的目标路径」。
  - **规则学习**：定期或按需从反馈库中提炼新关键词/扩展名，生成规则候选，供用户**一次性审核整批**采纳或丢弃，而不是逐条编辑。
  - **向量/排序学习**：将反馈作为正样本，更新「目标文件夹」的表示或排序模型，使相似项下次更易被推荐到正确目标。

---

## 五、Qwen 多模态、向量、排序的用法

| 能力 | 用途 |
|------|------|
| **Qwen 多模态** | 未命中规则时：对当前项（文件名 + 可选：文档摘要/图片描述）生成简短语义描述或候选类别，再映射到「目标文件夹名」或白名单。 |
| **向量模型** | 将「目标文件夹名 + 该文件夹下已有/历史整理项」向量化；当前项也向量化后做相似度检索，得到 Top‑N 候选目标。 |
| **排序模型** | 当存在多候选（规则命中多条或向量 Top‑N）时，用排序模型选最终一个目标，或输出置信度以决定「直接执行」还是「需用户确认」。 |

置信度低于阈值时，一律进入「需用户确认」流程，避免误移。

---

## 六、「不必一条条改规则」的两种方式

1. **由反馈自动提炼规则（推荐）**  
   - 从反馈库中按「目标路径」聚合，用启发式或轻量模型从「文件名/内容摘要」中抽取关键词与扩展名。  
   - 生成一批「规则候选」（name、keywords、extensions、target），在设置页或单独弹窗中**整表展示**，用户可勾选采纳、忽略或微调后采纳，**一次性**更新 `config.yaml` 的 `rules`。

2. **由模型建议整批规则**  
   - 输入：当前 `rules` + 反馈库中的 (文件名/摘要 → 目标)。  
   - 输出：模型建议的新增/修改规则列表（同样 name、keywords、extensions、target）。  
   - 用户对整批建议做一次性审核，采纳后合并进配置。

两者可并存：先自动提炼，再经模型补全或去重，最后用户一次性拍板。

---

## 七、数据与存储

- **反馈库**：建议在 `%APPDATA%\DesktopCleanup` 下新增存储（如 SQLite 或 JSON 文件），字段至少包含：原始路径/文件名、扩展名、可选内容摘要、用户采纳的目标路径、时间戳。  
- **分类缓存**：可复用或扩展反馈库，记录「文件名/路径 + 目标」，用于同一文件再次出现或相似文件推荐时的一致性。  
- **规则**：继续使用现有 `config.yaml` 的 `rules`；批量更新时在内存中合并用户采纳的候选，再整体写回。

---

## 八、与现有行为的关系

- 延迟时间、排除文件夹、快捷方式白名单、历史记录、托盘与设置页行为保持不变。
- 「从桌面学习」仍只更新目标路径候选与快捷方式白名单；**不**自动改规则内容；规则内容由「反馈提炼」或「模型建议 + 用户一次性审核」来更新。
- 设置页保留现有规则表格的逐条编辑能力，供高级用户微调；但日常以「批量建议 → 一次性审核」为主，减轻「一条条改」的负担。

---

## 九、后续可细化项

- 反馈库与分类缓存的具体 schema、索引与清理策略。
- 提炼规则的启发式/模型接口与 prompt 设计。
- 向量/排序模型的数据格式、更新频率与冷启动策略（目标少、历史少时的 fallback）。
- 设置页或独立入口的「规则建议」审核 UI 与交互。

---

## 附录 A：与 docs/qwen 的对应关系

本设计中的「Qwen 多模态、向量、排序」与项目内 **docs/qwen** 文档的对应关系如下，实现时可直接按这些 API 落地。

- **向量模型（文件名/摘要 → 目标文件夹匹配）**  
  - 使用 **`docs/qwen/向量化模型的详细使用说明.md`**：  
    - 纯文本（文件名、扩展名、简短描述）：`text-embedding-v4`，OpenAI 兼容或 DashScope `TextEmbedding.call`，建议 `dimension=1024`。  
    - 零样本「分类」：文档中的 **文本分类示例**（输入文本 + 候选标签列表，算向量相似度取最高）可直接用于「当前项 vs 目标文件夹名/白名单」的匹配。  
  - 多模态（需看图/文档内容时）：`qwen3-vl-embedding` 或 `tongyi-embedding-vision-plus` 的 **MultiModalEmbedding**（见该文档「多模态独立向量 / 多模态融合向量」），将文件名 + 可选图片/文本摘要融合为向量，再与各目标文件夹的表示做相似度比较。

- **LLM 生成类别/目标（需自然语言理解时）**  
  - 使用 **`docs/qwen/qwen3的DashScope API 参考.md`**：  
    - `dashscope.Generation.call`，`model` 选 qwen-plus / qwen-turbo 等；在 `messages` 中传入「目标文件夹列表或白名单」+「当前文件名/类型/可选摘要」，要求输出一个目标文件夹名或 JSON。  
  - 需要稳定结构时，结合 **`docs/qwen/qwen3的结构化输出.md`**：`response_format` 设为 `json_object` 或 `json_schema`，让模型直接返回如 `{"target": "投标与结算"}`，便于解析。

- **「排序」在本项目中的含义**  
  - docs/qwen 的向量文档中**没有单独的排序/rerank API**，而是用**向量相似度排序**（余弦相似度 + 取 Top‑1/Top‑N）。  
  - 本设计中的「排序模型」可落实为：对规则未命中项，用 **text-embedding-v4** 对「当前项描述」与「各目标文件夹名（或代表文本）」算相似度，按分数排序后取 Top‑1 作为推荐；若你方另有 Qwen 排序/rerank 接口，可替换为该接口对多候选做精排。

- **小结**  
  - 分类兜底：优先用 **向量相似度**（text-embedding-v4 + 零样本分类示例）在「目标文件夹列表」中选一个；需要更强语义时再调 **Generation** 做单次分类或整批规则建议。  
  - 多模态：按需使用 **MultiModalEmbedding**（见向量文档），与现有「文件名 + 可选内容」的设计一致。

---

## 附录 B：ai-file-sorter 源码关键片段（zread 扫库结果）

以下为使用 **zread** MCP 读取 `hyperfield/ai-file-sorter` 仓库后整理的关键片段，便于实现计划直接对齐其成熟做法。

### B.1 CategorizationService：Prompt 与请求

- **实现位置**：`app/lib/CategorizationService.cpp`（头文件 `app/include/CategorizationService.hpp`）。

- **LLM 响应格式**：模型返回 `category : subcategory`，解析用分隔符 `" : "`（见 `split_category_subcategory`）。空 subcategory 时用 category 作为 subcategory；category 为空时回退为 `"Uncategorized"`。

- **`build_whitelist_context()`**（白名单注入 prompt）：
```cpp
// 主类别：编号列表，要求 "pick exactly one label from the numbered list"
oss << "Allowed main categories (pick exactly one label from the numbered list):\n";
for (size_t i = 0; i < cats.size(); ++i)
    oss << (i + 1) << ") " << cats[i] << "\n";
// 子类别：有则同样编号列表；无则
oss << "Allowed subcategories: any (pick a specific, relevant subcategory; do not repeat the main category).";
```

- **`build_combined_context(hint_block)`**：按顺序拼接「语言说明」→「白名单块」（若启用）→「一致性 hint 块」，块之间用 `\n\n` 连接。即：`language_block + (whitelist_block) + hint_block`。

- **`format_hint_block(hints)`**（一致性提示文案）：
```text
Recent assignments for similar items:
- <category> : <subcategory>
- ...
Prefer one of the above when it fits; otherwise, choose the closest consistent alternative.
```

- **`run_llm_with_timeout`**：通过 `start_llm_future` 在独立线程中调用 `llm.categorize_file(item_name, item_path, file_type, consistency_context)`，主线程 `future.wait_for(timeout_seconds)`，默认本地 60s、远程 10s，可被环境变量 `AI_FILE_SORTER_LOCAL_LLM_TIMEOUT` / `AI_FILE_SORTER_REMOTE_LLM_TIMEOUT` 覆盖。

- **会话内一致性**：`SessionHistoryMap` 的 key 为 `make_file_signature(file_type, extension)`，即 `"FILE:.pdf"` 或 `"DIR:<none>"`；value 为最近若干条 `(category, subcategory)` 的 deque，最多 `kMaxConsistencyHints`（5）条。`collect_consistency_hints` 先查当前会话同 signature 的历史，不足时用 `db_manager.get_recent_categories_for_extension(extension, file_type, remaining)` 从 DB 补足。

### B.2 DatabaseManager：表结构与 key

- **实现位置**：`app/lib/DatabaseManager.cpp`。

- **主表 `file_categorization`**（缓存 key：`(file_name, file_type, dir_path)`，UNIQUE）：
```sql
CREATE TABLE IF NOT EXISTS file_categorization (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,   -- "F" | "D"
    dir_path TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    taxonomy_id INTEGER,
    categorization_style INTEGER DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_name, file_type, dir_path)
);
```

- **分类解析表 `category_taxonomy`**：存规范化的 category/subcategory，带 normalized 与 frequency；`category_alias` 存别名到 taxonomy id 的映射。`resolve_category(category, subcategory)` 会做规范化、查 canonical/alias、模糊匹配（相似度阈值 0.85），必要时 `create_taxonomy_entry`。

- **写入时机**：分类结果在 `update_storage_with_result` 中调用 `insert_or_update_file_with_categorization(file_name, file_type, dir_path, resolved, used_consistency_hints)`；用户在图审中修改后由 UI 侧写回（ConsistencyPassService 中 `apply_harmonized_update` 也会调同一接口）。`categorization_style` 用于记录是否使用了 consistency hints（0/1）。

- **按扩展名取近期分类**：`get_recent_categories_for_extension(extension, file_type, limit)` 按 `timestamp DESC` 查 `file_categorization`，过滤同 `file_type` 且文件名扩展名匹配的项，去重后返回最多 `limit` 条 `(category, subcategory)`，供 `collect_consistency_hints` 使用。

### B.3 ConsistencyPassService：「More consistent」批次内归一

- **实现位置**：`app/lib/ConsistencyPassService.cpp`。

- **用途**：在单次分类会话结束后，对已分类列表再做一次「一致性通过」：按 chunk（每批约 10 条）调用 LLM，输入当前 (category, subcategory) 与已知 taxonomy，要求输出统一后的分类，使同批内命名一致（如 "Docs" vs "Documents" 合并）。

- **Prompt 要点**（`build_consistency_prompt`）：说明为 taxonomy 归一助手；要求合并近义标签、保留原意、每行格式 `<id> => <Category> : <Subcategory>`，id 为文件全路径且与输入顺序一致，最后一行写 `END`。已知 taxonomy 以 JSON 数组形式注入。

- **响应解析**：优先解析 JSON 中的 `harmonized` 数组；失败则按行解析 `id => Category : Subcategory`，直至遇到 `END`。解析后对每条调用 `db_manager.resolve_category` 并 `insert_or_update_file_with_categorization` 写回缓存，同时更新内存中的 `CategorizedFile` 与 `newly_categorized_files` 对应项。

### B.4 与本设计的对应

| ai-file-sorter | 本设计 |
|----------------|--------|
| 白名单 + 会话内 hint | 目标文件夹列表 + 可选白名单；单次「立即整理」内可注入会话内一致性提示 |
| file_categorization 缓存 key | 反馈库/分类缓存可用 (dir_path, file_name, file_type) 或 (文件名, 扩展名) 为 key |
| ConsistencyPassService 批次归一 | 可选：单次整理完成后对当批推荐做一次一致性后处理或仅做会话内 hint，不做二次 LLM 也可 |
| taxonomy + alias + 模糊匹配 | 我们可简化为「目标路径列表 + 反馈库」；若需类别规范化可后续加类似 taxonomy 表 |

---

*设计说明结束。确认后可按此写实现计划（writing-plans）并分任务落地。*
