---
name: book-vault-analysis
description: "当用户提供本地图书文件 (EPUB/PDF/TXT, 中文可读或翻译版) 并希望生成完整的 Obsidian vault 分析时使用此 Skill。Skill 会将书分类到 14 大类 (文学/思想史/方法论/投资/商业/政经/历史/心理/科普/教育/艺术/育儿/旅行/混合) 之一, 然后按类型生成符合严格易读性约束 (C1-C12) 的 vault, 并通过 L1 (13-POINT 硬检查) + L2 (5 项软检查, 含占位符残留检测) 验证。输出位置: 由用户提供或记忆推断, 推荐 `<VAULT_PARENT>/<书名>/` (例如 `<USER_HOME>/github/book-notes/2025/灿烂千阳/`), 必含 `读书脑图.md` (MOC 入口)。Mermaid 关系图按类型使用专属模板 (人物关系图/概念图谱/理论关系图/框架图等)。字数规则: spine 字符数 ≥ 10,000 → `XX.X 万字`; < 10,000 → 整数。豆瓣数据以纯链接嵌入, 不嵌入封面图。占位符检测: 中间过程 (skill scaffold) 允许, 最终 vault 必须全部替换。通过率: ~15-20 分钟/本 (vs 手工 ~30 分钟)。"
version: 1.4.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [book, analysis, obsidian, mermaid, type-aware, 14-types, epub, vault, 图书分析, 笔记, placeholder-detection, cross-book-validator]
    category: productivity
    related_skills: []
    scripts: [scripts/s20_extract_epub_spine.py, scripts/s30_classify_book.py, scripts/s40_fetch_douban_data.py, scripts/s50_build_vault.py, scripts/s99_cleanup_residue.py, scripts/s90_validate_vault.py, scripts/s95_check_placeholders.py, scripts/s97_cross_book_validator.py]
    references: [PRD.md, references/14-types-taxonomy.md, references/c1-c12-readability.md, references/l1-validation.md, references/l2-finalize.md, references/placeholder-detection.md, references/moc-fields.md, references/douban-data.md, references/reading-methods.md, references/word-count.md, references/golden-sample.md, references/entity-extraction-template.md, references/poc-experience.md, references/l1-l2-pitfalls.md, references/epub-extraction-quirks.md, references/person-extraction.md, references/build-vault-pitfalls.md, references/chapter-notes-guide.md, references/wikilink-pitfalls.md, references/qa-pitfalls.md, references/llm-inference-pitfall.md]
---

# book-vault-analysis (图书 Obsidian 笔记自动生成)

## 概述

本 Skill 用于生成任何图书 (EPUB / PDF / TXT) 的完整 Obsidian vault 分析, 包含:

- **类型感知结构** (14 大类)
- **严格易读性约束** (C1-C12, 12 个强约束)
- **强制验证** (L1 13-POINT 硬检查 + L2 5 项软检查)
- **占位符残留检测** (中间过程允许, 最终 vault 必须全部替换)

Skill 特点: **确定性 + 自校正**
- 10 步工作流 (Step 0 → Step 9.6)
- 自动生成 wikilink (避免人肉笔误)
- 自动应用易读性约束
- 14 类型模板驱动 vault 结构
- 输出前必须通过 L1 + L2 + 占位符检测

**输入**: EPUB 文件路径
**输出**: 完整的 Obsidian vault, 含 100+ .md 文件, 已通过验证

**需求规范**: 完整 PRD 见 `PRD.md` (跨平台规范)

## 使用时机

满足以下所有条件时使用本 Skill:
- 用户提供本地图书文件 (`@file` / `@folder` / 显式路径)
- 该书是中文可读或翻译版 (文学 / 哲学 / 商业 / 历史 / 等)
- 用户希望做**深度阅读分析**用于 Obsidian (笔记 / 关系图 / 主题 / 摘录 / 章节 / 人物)
- 用户提到中文输出、Obsidian vault、读书笔记、笔记分析、人物关系图 / 主题分析 / 阅读问题 / 复习卡片

不要在以下场景使用:
- 修改源图书文件的任务 (源文件只读)
- 纯摘要 (200 字简短总结, 用其他 skill)
- 涉及 vault 和 /tmp/ 抽取之外的外部系统

## 脚本索引 (Script Index)

**序号前缀规则**: `s{NN}_<功能>.py`, `NN` 对应工作流步骤.

| Step | 脚本 | 功能 |
|---|---|---|
| Step 2 | `scripts/s20_extract_epub_spine.py` | EPUB → spine 抽取 |
| Step 3 | `scripts/s30_classify_book.py` | 14 大类分类 |
| Step 4 | `scripts/s40_fetch_douban_data.py` | 豆瓣数据抓取 (D1-D10) |
| Step 5-8 | `scripts/s50_build_vault.py` | scaffold / entities / mermaid / moc 四阶段 (`--phase=`) |
| Step 9 (L1) | `book-vault-analysis/scripts/s90_validate_vault.py` | L1 13-POINT 硬检查 |
| Step 9.5 | `scripts/s95_check_placeholders.py` | 占位符残留检测 (硬约束) |
| Step 9.6 | `book-vault-analysis/scripts/s96_finalize_vault.py` | L2 5 项软检查 |
| 维护 | `scripts/s99_cleanup_residue.py` | 残留清理 (跳过 `_backup`) |

**注**:
- `s50_build_vault.py` 是多功能脚本, 通过 `--phase={scaffold,entities,mermaid,moc}` 切换.
- `s09` 和 `s96` 物理上位于 `book-vault-analysis/scripts/`, 命名风格一致.

## 路径变量

```
EPUB    = <EPUB_SOURCE_DIR>/<书名>.epub        (用户提供)
VAULT   = <VAULT_PARENT>/<书名>/               (用户提供或默认当前目录)
SCRATCH = <临时目录>/<书名-stem>/spine/         (skill 自动选择, e.g. /tmp/literary-scratch/)
TEMPLATE = ~/.hermes/skills/productivity/book-vault-analysis/templates/T{N}.json
```

**示例** (用户当前常用):
- `EPUB_SOURCE_DIR = <USER_HOME>/Documents/图书/`
- `VAULT_PARENT = <WORKSPACE>/2025/`
- `SCRATCH = /tmp/literary-scratch/`

`<书名-stem>` 是文件名安全形式 (无 `/` `?` `:`). `<书名>` 是用户可见的书名。

## 工作流 (10 步)

### Step 0 — 前置校验 (Pre-flight Check)

```
✓ 输入文件存在, 是 .epub, 大小 > 1KB
✓ EPUB_SOURCE_DIR 路径合法 (用户提供)
✓ 输出 vault 路径不冲突
✓ EPUB hash 已记录 (md5sum)
✓ 类型置信度 ≥ 0.85, 否则询问用户
```

**任一失败 → 停止, 不继续**

### Step 1 — 定位源 (Identify the source)

源路径在 `<EPUB_SOURCE_DIR>` (用户提供, 默认从记忆推断)。**只读**。

当用户说"分析《书名》"而未给路径时:
1. 递归 glob `<EPUB_SOURCE_DIR>/**/*.{epub,azw,azw3,mobi,pdf}`
2. fuzzy-match 文件名与书名
3. 唯一匹配 → 直接用
4. 多个匹配 → 选最近的 (mtime 最大)
5. 无匹配 → 询问用户

**绝不修改** `<EPUB_SOURCE_DIR>` 下的任何东西。

### Step 2 — 抽取到 SCRATCH

执行: `python3 scripts/s20_extract_epub_spine.py <EPUB> <SCRATCH>`

- 读 OPF, 解析 spine, 每个 spine 文件保存为 `spine_NNN-slug.txt`
- 保存 metadata.json (title, creator, publisher, contributors)
- **不修改原 EPUB** (前后比对 hash)

### Step 3 — 分类图书 (14 大类)

执行: `python3 scripts/s30_classify_book.py <SCRATCH>/metadata.json`

读 OPF metadata + 豆瓣数据 + LLM 知识 → 输出 `{main: "T1", sub: "小说"}`.

14 类型见 `references/14-types-taxonomy.md`:
- T1 文学, T2 思想史, T3 方法论, T4 投资, T5 商业, T6 政经
- T7 历史, T8 心理, T9 科普, T10 教育, T11 艺术, T12 育儿, T13 旅行
- T14 混合 (如 文学+哲学, 历史+旅行)

### Step 4 — 抓取豆瓣数据

执行: `python3 scripts/s40_fetch_douban_data.py <书名> <作者> [ISBN]`

脚本实现 D1-D10:
1. ISBN 直接 → `/subject/<isbn>/`
2. 搜索兜底 → `?search_text=<书名>+<作者>&cat=1001`
3. 用户 URL 优先 (如有)
4. 提取: 评分、评价人数、Top250 排名、评分分布
5. Top 5 短评精选 (评价人数 < 5 则跳过, 不写占位)
6. 同译本搜索链接 (≥ 2 同名 subject)
7. 同类型更高分提醒 (title-match 验证)

### Step 5 — 构建通用骨架 (Global Scaffold)

执行: `python3 scripts/s50_build_vault.py <VAULT> --phase=scaffold`

创建 9 个根目录文件 + 4 个通用子目录:

```
${VAULT}/
├── 00-封面.md
├── 01-导言-评论.md
├── 读书脑图.md          ← MOC 入口 (无 NN- 前缀)
├── 无剧透导读.md
├── 全书结构.md
├── 章节地图.md          ← 初始为空, Step 6/7 填入
├── 主题与核心观点.md
├── 阅读问题.md
├── 复习卡片.md
├── README.md
├── 概念/  (5-8 个 .md, Step 6 填入)
├── 主题/  (5 个 .md, Step 6 填入)
├── 摘录/  (5 个 .md, Step 6 填入)
└── 章节/  (Step 6 填入)
```

### Step 6 — 构建类型化实体 (Type-Specific Entities)

执行: `python3 scripts/s50_build_vault.py <VAULT> --phase=entities --type=T{N}`

加载 `templates/T{N}.json` (14 类型模板) 并填充:
- 类型化子目录 (例如 T1 文学 → 人物/事件/地点; T2 思想史 → 思想家/概念/思想流派)
- 5-30 个实体文件 (每个 200-500 字)
- 自动生成 wikilink (例如 `[[主题-阿富汗女性的双重压迫]]` 对应 `主题/主题-阿富汗女性的双重压迫.md`)

然后填充章节/ 子目录:
- `章节/1-第一部名/` `00-前言-第一部名.md` (无冲突命名)
- `章节/N-部名/NN-第N章.md` 每个章节 (例如 51 章《灿烂千阳》)
- 附录: `52-后记.md`, `53-致谢.md`, `54-附录.md`, `55-译后记.md`, `56-版权.md`

**关键: 所有 wikilink 由脚本自动生成, 避免人肉笔误**。

### Step 7 — 生成 Mermaid (类型化)

执行: `python3 scripts/s50_build_vault.py <VAULT> --phase=mermaid --type=T{N}`

生成 `<类型>mermaid.mermaid.md`:
- T1 文学 → `人物关系图.mermaid.md`
- T2 思想史 → `思想影响图.mermaid.md`
- T3 方法论 → `概念图谱.mermaid.md`
- T4 投资 → `理论关系图.mermaid.md`
- T5 商业 → `框架图.mermaid.md`
- T6 政经 → `阵营-人物图.mermaid.md`
- T7 历史 → `时间线-人物图.mermaid.md`
- T8 心理 → `概念图谱.mermaid.md`
- T9 科普 → `概念关系图.mermaid.md`
- T10 教育 → `概念图谱.mermaid.md`
- T11 艺术 → `人物-风格图.mermaid.md`
- T12 育儿 → `概念图谱.mermaid.md`
- T13 旅行 → `人物-地点图.mermaid.md`
- T14 混合 → `类型化 mermaid`

**Mermaid 规则** (自动强制):
- 避免中文 parens in subgraph names (用 " - " 或引号替代)
- 用 `<br/>` 在节点标签里换行
- 按角色类型上色 (主角红/反派黑/朋友蓝)
- 边标签用 `-->|label|` 语法, 类型化关系

### Step 8 — 更新 MOC + 阅读方式 + 短评

执行: `python3 scripts/s50_build_vault.py <VAULT> --phase=moc`

更新 `读书脑图.md`, 含所有自动生成的交叉引用。

**MOC 结构** (必含字段, 按顺序):
1. `## 书籍信息` — 10 字段 (作者/译者/出版社/出版年/ISBN/页数/原作名/**类型**/**字数**/豆瓣评分)
2. `## 豆瓣数据` — 豆瓣块 (纯链接, 含短评精选)
3. `## 阅读方式` — 4-5 项 (从标准阅读法列表中选)
4. `## 章节结构` — 自动生成 51 章 wikilink 列表
5. `## 涉及人物` (或类型化对应) — 自动生成所有实体 wikilink
6. `## 核心概念` — 5 项
7. `## 主题` — 5 项
8. `## 关键摘录` — 5 项
9. `## 阅读路径` — pre/mid/post 阅读
10. `## 关系图` — Mermaid 文件入链

### Step 9 — 验证 L1 + L2 (强制)

执行:
```bash
cd <vault_root>
python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/s90_validate_vault.py "<书名>"
python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/s96_finalize_vault.py "<书名>"
```

**L1 13-POINT 硬检查**: source, paths, no/Users, no <USER>, no sources, no book-analysis, no /tmp/, no 外部路径/占位/已弃用, no empty, no broken wikilinks, no orphans, Mermaid parses, Excalidraw parses.

**失败处理**:
- L1 失败 → 回到 Step 6/7/8 修复 → 重新校验
- 在 `ALL HARD CHECKS PASSED` 之前不得声明成功

### Step 9.5 — 占位符残留检测 (硬约束)

执行:
```bash
python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/s95_check_placeholders.py "<vault_path>"
# 或:
python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/s96_finalize_vault.py "<vault_path>"  # 包含此检查
```

**核心规则**:
- ✅ **中间过程** (skill scaffold Step 5): 允许占位符 (模板)
- ❌ **最终 vault** (Step 9.5+): **禁止任何占位符**

**检测模式** (10 类):
1. `(待 X 填入)` - skill 模板
2. `(由 LLM...填入)` - 老式
3. `(由 X 填入)` - 通用
4. `(由 Step X 填入)` - 老式
5. `(Step X 填入)` - 老式
6. `(由 author_intro 填入)` - 豆瓣占位
7. `(由 content_intro 填入)` - 豆瓣占位
8. `(由 douban 填入)` - 豆瓣占位 (i 模式)
9. `(LLM 内容生成填入)` - 老式

**输出格式**:
```
[5] Unfilled placeholder residue (HARD)
    ✓ No unfilled placeholders — vault is publish-ready
```

或:
```
[5] Unfilled placeholder residue (HARD)
    ! 5 unfilled placeholder(s):
      灿烂千阳/读书脑图.md:
        L11: (待 entities phase 自动填入)
        L15: (由 LLM 抽取后填入)
        ... and 3 more
```

**失败处理**:
- 发现占位符 → FAIL + exit 1
- 回到 Step 6/7/8 替换占位符
- 重新运行检测

完整规则见 `references/placeholder-detection.md`.

### Step 9.6 — 软检查 (s96_finalize_vault.py)

**L2 5 项软检查**:
1. File-level anomalies (零字节, 异常字符)
2. Frontmatter hygiene (title + type 完整)
3. Wikilink network reachability (BFS from MOC)
4. Extra residue scan (TODO/FIXME/MOC- 等)
5. Unfilled placeholder residue (硬约束)

**输出**: 详细的 5 项报告 + SUMMARY (hard / soft 计数)

**通过标准**: `hard = 0`, `soft` 可接受

### 总验证流程

```
Step 9 (L1) → ALL HARD CHECKS PASSED
Step 9.5 (placeholder) → No unfilled placeholders
Step 9.6 (L2) → hard = 0, soft = N
                ↓
            全部 PASS → vault publish-ready
            任一 FAIL → 回到 Step 6/7/8 修复
```

## 12 个易读性约束 (C1-C12)

完整说明见 `references/c1-c12-readability.md`。摘要:

| # | 约束 | 实现 |
|---|---|---|
| C1 | 章节文件 `NN-XXX.md` 排序 | `s50_build_vault.py` 强制加 NN- 前缀 |
| C2 | 段落 ≤ 8 行 | LLM prompt 强制 |
| C3 | 标题层级 ≤ `####` | LLM prompt 强制 |
| C4 | 引文 `> blockquote` 原文 | LLM prompt: "不要改写原文" |
| C5 | 表格列数 ≤ 5 | 手工设计, LLM 强制 |
| C6 | 不嵌入图片 | `s40_fetch_douban_data.py` 不提取图片 |
| C7 | 段间空行 | `s50_build_vault.py` 标准化空白 |
| C8 | 中文全角标点 | LLM prompt 强制 |
| C9 | 数字格式 `XX.X 万字` | `s50_build_vault.py` 格式化字数 |
| C10 | `[[wikilink]]` 双中括号 | 所有 wikilink 自动生成, 无人肉笔误 |
| C11 | 日期 ISO 8601 | 全部用 `2026-07-20` 格式 |
| C12 | 字数规则 | `s50_build_vault.py` 读 spine 字符数格式化 |

## 14 类型模板 (T1-T14)

完整 schema 见 `templates/T{1-14}.json`。每个模板定义:
- `vault_subdirs`: 类型化目录 (e.g., T1 文学 → 人物/事件/地点)
- `mermaid_filename`: 类型化 Mermaid 名
- `extraction_prompt`: LLM 实体抽取 prompt
- `entity_count_range`: [min, max] 实体数

## 已知陷阱

1. **不要修改 EPUB** (只读契约). 前后对比 hash.
2. **不要嵌入封面图** in vault (用户明确拒绝).
3. **用 bare stem wikilink** (无路径前缀如 `[[1-第一章]]`). Obsidian 会全局搜索.
4. **文件名必须 stem 唯一** (L1 的 `note_names` 用 `f.stem`). 例如多个 `00-前言-XXX.md` 在不同子目录需要唯一 stem 名.
5. **Mermaid subgraphs**: 避免中文 parens (用 " - " 替代).
6. **不要创建 folder-alias 页面** (例如根目录的 `人物.md`). 用 `**人物/**` 加粗文本替代.
7. **一本书一个 vault** — 永远不要把两本书混在一个 vault.
8. **在 vault 根目录运行 L1 + L2 验证** (脚本用 `os.getcwd()` 找 vault).

## ⚠️ 禁止 LLM 启发式推断作者 (跨书内容污染防控)

**问题**: 当 `s40_fetch_douban_data.py` 失败 (豆瓣屏蔽, 返回 `isbn: null`, `subject_id` 缺失) 时, LLM 会用**训练记忆**"推断" 作者和背景, 经常**跨书污染** (把书 A 误填为作者 B 的作品, 引用作者 B 的元素).

**强制规则** (5 条):

1. **豆瓣数据失败 = 数据缺失, 不是推断**. 当 `isbn`/`subject_id`/`rating`/`hot_comments` 任一缺失时, MOC 的**作者/译者/出版社/出版年/ISBN/页数/原作名/字数/豆瓣评分**字段必须留 `[待豆瓣数据嵌入后填入]` 或 `[豆瓣暂无数据]`, **不写猜测**.
2. **作者和场景必须从 spine 内容推断**, 不从训练记忆:
   - 读 `/tmp/literary-scratch/<书名>/spine/*.txt` 找城市名/关键人物/后记作者自述
   - 读 `/tmp/literary-scratch/<书名>/metadata.json` 看 OPF dc:creator/dc:title
3. **严禁"风格延续假设"**: 如果用户之前分析过同作者另一本, LLM 不能把作者风格套到新书上.
4. **严禁"同主题推断作者"**: 同主题不代表同作者.
5. **检测**: 在 vault 生成后, 用 `scripts/s97_cross_book_validator.py <vault_path> T{N}` 检查类型错配. 该脚本只检查"非本书类型" 的高频术语, 不硬编码具体作者元素.

**修复脚本**:

```bash
python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/s97_cross_book_validator.py "<vault_path>" "<vault_type>"
```

**配置化误植规则** (在 `scripts/s97_cross_book_validator.py` 的 `TYPE_FORBIDDEN_PATTERNS` 字典):

- T1 文学: 不应高频出现 T4 投资 / T5 商业 / T6 政经 专属术语
- T4 投资: 不应高频出现 T6 政经 专属术语
- T13 旅行: 不应高频出现 T2 思想史 / T6 政经 专属术语

详见 `references/llm-inference-pitfall.md`.

## 性能

- **手工** (手写 100+ 文件): ~30 分钟/本
- **本 skill 自动化**: ~15-20 分钟/本
- **17 本书总耗时**: ~4-5 小时 (vs 8-9 小时手工)

主要节省: 自动生成 wikilink (避免人肉笔误) + 预建类型模板。

## 测试样本

`assets/golden-灿烂千阳/` 是完整参考实现 (116 .md 文件, L1+L2 PASS)。

## 相关 Skill

