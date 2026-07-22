# PRD v2: 图书 Obsidian 笔记自动生成 (跨平台需求规范)

> **版本**: v2.2 (2026-07-22: 新增 s97_cross_book_validator.py + 跨书内容污染防控规则 + D0 数据缺失约束)
> **状态**: PRD (需求规范) — 不是执行脚本
> **目标**: 给定一个 EPUB → 输出符合规范的 Obsidian vault
> **平台无关**: 本 PRD 不绑定任何 AI Agent, 可在任何平台实现

## 〇、文档目的

本 PRD 定义**图书 Obsidian 笔记自动生成**的完整需求。

- **跨平台**: 任何 AI Agent 都能基于本 PRD 实现
- **跨实现**: 不同平台可以用不同脚本语言实现

## 一、核心决策

| 项 | 决定 |
|---|---|
| 触发 | 用户说"分析《书名》"或给定 EPUB 路径 |
| 输出 | 14 大类适配的 Obsidian vault |
| 类型体系 | **14 大类** (不预留扩展) |
| Skill 结构 | 1 个总 skill (内部按类型路由) |
| 模板结构 | 通用模板 + 类型化扩展 |
| 校验分层 | L1 13-POINT + L2 5 项 (含占位符硬约束) |
| 可迁移性 | 可恢复 + 可移植 + 可读 + 可测试 |

## 一.5、脚本索引 (Script Index)

**序号前缀规则**: `s{NN}_<功能>.py`, 其中 `NN` 对应工作流步骤编号.

| Step | 脚本 | 功能 |
|---|---|---|
| Step 2 | `scripts/s20_extract_epub_spine.py` | EPUB → spine 抽取 |
| Step 3 | `scripts/s30_classify_book.py` | 14 大类分类 |
| Step 4 | `scripts/s40_fetch_douban_data.py` | 豆瓣数据抓取 (D1-D10) |
| Step 5-8 | `scripts/s50_build_vault.py` | scaffold / entities / mermaid / moc 四阶段 |
| Step 9 (L1) | `scripts/s90_validate_vault.py` | L1 13-POINT 硬检查 |
| Step 9.5 | `scripts/s95_check_placeholders.py` | 占位符残留检测 (硬约束) |
| Step 9.6 | `scripts/s96_finalize_vault.py` | L2 5 项软检查 |
| **Step 9.7** (新增) | `scripts/s97_cross_book_validator.py` | **跨书内容污染检测 (类型错配) - 必检** |
| 维护 | `scripts/s99_cleanup_residue.py` | 残留清理 (跳过 `_backup`) |

**注**:
- `s50_build_vault.py` 是多功能脚本, 通过 `--phase={scaffold,entities,mermaid,moc}` 选择.
- `s09` 和 `s96` 物理上在 `book-vault-analysis/scripts/`, 但命名风格一致.
- 完整的命名映射见 `SKILL.md`.

## 二、14 大类 (Book Type Taxonomy)

| # | 大类 | 小类 | vault 子目录 | Mermaid 文件名 |
|---|---|---|---|---|
| **T1** | 文学 | 小说 / 短篇 / 散文 / 诗歌 / 纪实文学 | `人物/` `事件/` `地点/` | `人物关系图.mermaid.md` |
| **T2** | 思想史/哲学 | 哲学 / 思想史 / 思想评论 | `思想家/` `概念/` `思想流派/` | `思想影响图.mermaid.md` |
| **T3** | 方法论/自助 | 时间管理 / 学习方法 / 习惯养成 | `概念/` `方法/` `步骤/` | `概念图谱.mermaid.md` |
| **T4** | 投资/经济 | 价值投资 / 宏观 / 周期 / 经济学 | `思想家/` `理论/` `模型/` `案例/` | `理论关系图.mermaid.md` |
| **T5** | 商业/管理 | 商业 / 创业 / 管理 / 营销 | `原则/` `案例/` `框架/` | `框架图.mermaid.md` |
| **T6** | 政经/时政 | 政治评论 / 国际关系 / 政策分析 | `人物/` `事件/` `阵营/` `概念/` | `阵营-人物图.mermaid.md` |
| **T7** | 历史/纪实 | 历史 / 传记 / 游记 / 纪实 | `人物/` `事件/` `地点/` `概念/` | `时间线-人物图.mermaid.md` |
| **T8** | 心理/自助 | 心理学 / 情绪管理 / 自助 | `概念/` `理论/` `方法/` `案例/` | `概念图谱.mermaid.md` |
| **T9** | 科普/科学 | 科学 / 自然 / 技术 / 医学 | `概念/` `理论/` `案例/` `原理/` | `概念关系图.mermaid.md` |
| **T10** | 教育/学习 | 教育 / 育儿 / 学习方法 | `概念/` `理论/` `方法/` `案例/` | `概念图谱.mermaid.md` |
| **T11** | 艺术/设计 | 艺术 / 设计 / 建筑 / 摄影 | `人物/` `作品/` `风格/` `概念/` | `人物-风格图.mermaid.md` |
| **T12** | 育儿/家庭 | 育儿 / 家庭 / 健康 / 养生 | `概念/` `方法/` `案例/` | `概念图谱.mermaid.md` |
| **T13** | 旅行/地理 | 旅行文学 / 游记 / 地理 / 文化 | `地点/` `人物/` `事件/` `概念/` | `人物-地点图.mermaid.md` |
| **T14** | 混合 (跨大类) | 文学+哲学 / 历史+旅行 | 跨类型组合 | 类型化 |

## 三、10 步工作流 (Workflow)

### Step 0: Pre-flight Check (前置校验)

```
□ 输入文件存在, 是 .epub / .pdf / .txt
□ 文件大小 > 1KB
□ EPUB hash 记录 (md5sum)
□ 输出 vault 路径不冲突
□ LLM 分类置信度 ≥ 0.85 (高) 或已询问用户 (低)
```

**任一失败 → 报错停止**

### Step 1: Identify the source (定位源)
- 用户给定 EPUB 路径
- 如果没有, 在源目录递归 glob + fuzzy-match
- 校验文件存在 + 大小 > 1KB

### Step 2: Extract to 临时目录/<书名>/
- 读 OPF → 解析 spine
- 输出 N 个 spine_NNN-slug.txt
- **强约束**: 不修改原 EPUB (hash 比对)
- **脚本**: `scripts/s20_extract_epub_spine.py`

### Step 3: Classify the book (14 大类分类)
- 启发式匹配 (书名关键词 + 元数据)
- 置信度 ≥ 0.85 → 自动确认; < 0.85 → 询问用户
- **脚本**: `scripts/s30_classify_book.py`

### Step 4: Fetch Douban data (豆瓣数据)
- **D1** ISBN 直接跳转
- **D2** 搜索兜底
- **D3** 用户提供的 URL 优先
- **D4** Top250 排名
- **D5** 评分分布
- **D6** Top 5 短评精选 (评价人数 ≥ 5)
- **D7** 同译本搜索链接 (≥ 2 同名 subject)
- **D8** 同类型更高分提醒
- **D9** 内容简介/作者简介
- **D10** 嵌入 MOC
- **脚本**: `scripts/s40_fetch_douban_data.py`

### Step 5: Build the global scaffold (通用骨架)
- 9 个根目录文件 + 4 个通用子目录
- 类型化子目录用 placeholder
- 强约束: 通用部分对所有类型一致
- **脚本**: `scripts/s50_build_vault.py --phase=scaffold`

### Step 6: Extract type-specific entities (类型化实体抽取)
- 根据 Step 3 分类 → 加载 `templates/T{N}.json`
- LLM 抽取 5-30 个实体
- 实体档案: 200+ 字简介 + 关键事件 + 关系网络
- **脚本**: `scripts/s50_build_vault.py --phase=entities --people-json=... --concepts-json=... --themes-json=... --quotes-json=... --chapters-json=...`

### Step 7: Generate type-specific Mermaid (类型化 Mermaid)
- 5-30 个节点, subgraph 分组
- 强约束: 避免中文 parens in subgraph names
- **脚本**: `scripts/s50_build_vault.py --phase=mermaid --mermaid-content=<file>`

### Step 8: Update MOC + Generate root nav (MOC + 根目录导览)
- MOC 必含字段 (详见第五章)
- 类型化 MOC 字段: `<类型>图 → [[<类型>图.mermaid]]`
- **脚本**: `scripts/s50_build_vault.py --phase=moc --moc-content=<file>`

### Step 9: Verify L1 + L2 (校验)
- **L1 13-POINT**: 硬检查
- **L1 #14 整书双链校验** (新增): 所有 .md 文件能从 MOC BFS 到达
- **L2 5 项检查**: 4 软 + 1 硬 (占位符残留, 在 Step 9.6 详细展开)
- **Step 9.5 占位符残留检测** (新增, 硬约束): 中间过程允许, 最终 vault 必须全部替换
- **Step 9.6 软检查** (`s96_finalize_vault.py`): 5 项检查 (4 软 + 1 硬: 占位符)
- **Step 9.7 跨书内容污染检测** (`s97_cross_book_validator.py`, 新增, 硬约束): 检测"非本书类型" 的高频术语. 调用方式:
  ```bash
  python3 scripts/s97_cross_book_validator.py "<vault_path>" "<vault_type>"
  ```
  失败 → Step 6/7/8 修复 → 重新校验
- **脚本**:
  - L1 硬检查: `scripts/s90_validate_vault.py <vault>`
  - Step 9.5 占位符: `scripts/s95_check_placeholders.py <vault>`
  - Step 9.6 L2 软检查: `scripts/s96_finalize_vault.py <vault>`
  - Step 9.7 跨书污染: `scripts/s97_cross_book_validator.py <vault> T{N}`
- 失败 → 回到 Step 6/7/8 修复 → 重新校验

### 维护 (可选)
- **脚本**: `scripts/s99_cleanup_residue.py` (清理残留, 跳过 `_backup` 后缀目录)

### 占位符残留检测 (Step 9.5, 新增硬约束)

**核心规则**:
- ✅ **中间过程** (skill scaffold Step 5): 允许占位符 (模板待填充)
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

**失败处理**: 列出具体文件:行号 → 回到 Step 6/7/8 替换 → 重新检测

## 四、12 个易读性硬约束 (C1-C12)

| # | 约束 | 规则 | 实现 |
|---|---|---|---|
| **C1** | 章节排序 | 章节文件 `NN-XXX.md`, 部目录 `1-XXX/`, `2-XXX/` | 文件命名 |
| **C2** | 段落长度 | 每段 ≤ 8 行 (移动端友好) | 内容生成 |
| **C3** | 标题层级 | 最多 `####` (禁用 `#####+`) | 内容生成 |
| **C4** | 引文格式 | 原文用 `> blockquote`, 禁止 LLM 改写 | 引用规范 |
| **C5** | 表格列数 | ≤ 5 列 | 内容生成 |
| **C6** | 图片 | 不嵌入 base64, 不引用绝对路径 | 内容生成 |
| **C7** | 段间空行 | 每个段落前后必须有空行 | 内容生成 |
| **C8** | 中文全角标点 | 强制 `，。！？；：（）「」` | 内容生成 |
| **C9** | 数字格式 | `21.6 万字` `8.7 万字` | 内容生成 |
| **C10** | 内部链接 | 强制 `[[wikilink]]` 双中括号 | 内容生成 |
| **C11** | 日期格式 | frontmatter ISO 8601 `2026-07-20` | frontmatter |
| **C12** | 字数规则 | ≥ 10,000 → `XX.X 万字`, < 10,000 → 整数, 禁止双口径 | 内容生成 |

## 五、MOC 字段顺序 (Mandatory)

`读书脑图.md` 必须按以下顺序:

```
## 书籍信息

1. 作者：[XX]
2. 译者：[XX] (如有)
3. 出版社：[XX]
4. 出版年：[XX]
5. ISBN：[XX]
6. 页数：[XX]
7. 原作名：[XX] (如有)
8. **类型：T1 文学 - 小说**        ← 必含
9. **字数：21.6 万字**                ← 必含
10. 豆瓣评分：X.X / NNNN 人评价
```

## 六、豆瓣处理 (D1-D10)

| # | 规则 | 触发 | 输出 |
|---|---|---|---|
| D1 | ISBN 直接跳转 | EPUB 有 ISBN | `/subject/<isbn>/` |
| D2 | 搜索兜底 | D1 失败 | `?search_text=<书名>+<作者>&cat=1001` |
| D3 | 用户 URL 优先 | 用户提供 | 直接用 |
| D4 | Top250 排名 | subject 在 Top250 | `No.88 豆瓣图书 Top250` |
| D5 | 评分分布 | 任意 | `5★ 58.5% / 4★ 34.3% / ...` |
| D6 | Top 5 短评 | 评价人数 ≥ 5 | ≤ 5 条 hot comments |
| D7 | 同译本搜索链接 | ≥ 2 同名 subject | `> 📚 豆瓣搜索: [链接]` |
| D8 | 同类型更高分提醒 | 候选中更高分 | `> ⚠️ 提示: [书名] 评分 X.X` |
| D9 | 内容/作者简介 | 任意 | 原文搬运, 不改写 |
| D10 | 嵌入 MOC | 任意 | `## 豆瓣数据` 段 |
| **D0** (新增, 硬约束) | **豆瓣数据缺失处理** | `isbn=null`, `subject_id=0`, `rating=0`, `hot_comments=[]` 任一缺失 | **禁止**凭训练记忆填空. 必填 `[待豆瓣数据嵌入后填入]` 或 `[豆瓣暂无数据]` 占位. |

**D0 详细规则** (跨书内容污染防控):

当 `s40_fetch_douban_data.py` 抓取失败时, MOC 的**作者/译者/出版社/出版年/ISBN/页数/原作名/字数/豆瓣评分**字段**必须**留占位符 `[待豆瓣数据嵌入后填入]` 或 `[豆瓣暂无数据]`, **禁止**写猜测.

**作者识别 fallback 链** (按优先级):
1. 豆瓣数据 (D1-D9) — 最佳
2. OPF metadata (`dc:creator` / `dc:title`) — 可靠
3. spine 后记中的作者自述 (如 "我出版第一本长篇是 2007 年") — 可靠
4. spine 中的城市名/关键人物 — 中等
5. **以上均无** → 留 `[豆瓣暂无数据]`, **严禁**用训练记忆

**禁止的推断** (5 条):
- 严禁"风格延续假设": 同 session 内分析过的作者, 不能套到新书
- 严禁"同主题推断作者": 同主题不代表同作者
- 严禁凭书名/出版社/作者名"联想"
- 严禁在 MOC 中引用未在豆瓣/OPF 出现的关联作品
- 严禁在 LLM 抽取概念时用训练记忆填补

**检测脚本** (`scripts/s97_cross_book_validator.py`):

```bash
python3 scripts/s97_cross_book_validator.py "<vault_path>" "<vault_type>"
# e.g. python3 s97_cross_book_validator.py "仙症" T1
# 输出: ✅ no type-mismatch pollution detected
```

该脚本基于 **vault 类型**检测"非本书类型的高频术语" (通用规则, 不硬编码特定作者/作品). 详见 `references/llm-inference-pitfall.md`.

## 七、阅读方式 (R1)

MOC 必含 `## 阅读方式` 段, 4-5 种阅读法 (中文 + 英文双语命名):

**7 种基础阅读法** (最低必选 4 种):
1. 顺序阅读 (Sequential reading)
2. 精读 (Close reading)
3. 主题阅读 (Syntopical reading)
4. 重复阅读 (Re-reading)
5. 检视阅读 (Survey reading)
6. 批判性阅读 (Critical reading)
7. 比较阅读 (Comparative reading)

**类型化推荐**:
- 文学: 顺序 + 精读 + 沉浸式 + 主题 + 重复
- 思想史: 精读 + 主题 + 比较 + 批读 + 重复
- 方法论: 精读 + 主题 + FM3 + 费曼 + 重复
- 投资: 略读 + 精读 + 批判性 + 主题 + 重复

## 八、整书双链完整性校验 (L1 #14, 新增)

Step 9 增加:

```
□ 所有 .md 文件 (除 MOC) 都能从 MOC 通过 BFS 到达
□ MOC 的所有 [[wikilink]] 都指向存在的文件
□ 章节子目录的所有文件都至少被一处链接
□ 人物/概念/主题/摘录 等子目录都被 MOC 提及
□ MOC 自身无 broken self-reference
```

**失败 → 回到 Step 6/7/8 修复 → 重新校验**

## 九、L1 13-POINT 硬检查

| # | 检查 |
|---|---|
| 1 | source unchanged (EPUB hash 一致) |
| 2 | epub integrity (EPUB 可正常打开) |
| 3 | no /Users paths |
| 4 | no <USER> |
| 5 | no sources/X.txt |
| 6 | no book-analysis |
| 7 | no /tmp/ |
| 8 | no 外部路径/占位/已弃用 |
| 9 | no empty/short notes |
| 10 | 0 broken wikilinks |
| 11 | 0 orphans |
| 12 | Mermaid parses |
| 13 | Excalidraw parses (optional) |

## 十、L2 5 项软检查 (含占位符检测)

| # | 检查 | 类型 |
|---|---|---|
| 1 | File-level anomalies (零字节, 异常字符) | 软 |
| 2 | Frontmatter hygiene (所有 .md 有 title + type) | 软 |
| 3 | Wikilink network reachability (BFS from MOC) | 软 |
| 4 | Extra residue scan (占位/已弃用/TODO) | 软 |
| 5 | **Unfilled placeholder residue** | **硬** (新增) |

**核心区分**:
- 软检查: 输出警告, 不阻止发布
- 硬检查 (新增 #5): 占位符残留 = 必须修复, exit code 1

**L2 输出**: `SUMMARY  ::  hard = N  soft = M`
- `hard = 0` 必须满足
- `soft` 可接受

## 十一、状态检查 (每步之间)

| Step | 检查项 |
|---|---|
| 0 → 1 | 所有 pre-flight OK |
| 1 → 2 | EPUB 路径已记录, hash 记录 |
| 2 → 3 | spine 文件已生成, 字符数 > 5000 |
| 3 → 4 | 分类结果明确 (T1-T14 + 小类), 置信度 ≥ 0.5 |
| 4 → 5 | 豆瓣数据已嵌入 MOC |
| 5 → 6 | 通用骨架文件已存在 (含占位符, OK) |
| 6 → 7 | 类型化实体文件数 ≥ 5 (LLM 已替换占位符) |
| 7 → 8 | Mermaid 语法通过 |
| 8 → 9 | MOC 必含字段完整 |
| 9 → 9.5 | L1 13-POINT 全部 PASSED |
| 9.5 → 9.6 | 占位符残留检测 PASS (无任何 `(待 X 填入)` 类) |
| 9.6 → 9.7 | L2 5 项检查 PASS (hard=0) |
| 9.7 → 输出 | 跨书内容污染检测 PASS (`✅ no type-mismatch pollution detected`) |


## 十二、关键 References

实现细节 / 文档规范:

| 文件 | 用途 |
|---|---|
| `references/14-types-taxonomy.md` | 14 大类详细 schema |
| `references/c1-c12-readability.md` | 12 个易读性约束详解 |
| `references/l1-validation.md` | L1 13-POINT 硬检查详细规则 |
| `references/l2-finalize.md` | L2 5 项软检查详细规则 |
| `references/placeholder-detection.md` | 占位符检测 10 类模式 |
| `references/moc-fields.md` | MOC 11 个 section 详细 |
| `references/douban-data.md` | 豆瓣 D1-D10 数据规范 |
| `references/reading-methods.md` | 7 种阅读法 |
| `references/word-count.md` | 字数格式规则 |
| `references/golden-sample.md` | 黄金样本参考 |
| `references/entity-extraction-template.md` | LLM 实体抽取 prompt |
| `references/poc-experience.md` | POC 早期经验 |
| `references/l1-l2-pitfalls.md` | L1/L2 检查的边角问题 |
| `references/epub-extraction-quirks.md` | EPUB 抽取 quirks |
| `references/person-extraction.md` | 人物抽取方法论 |
| `references/build-vault-pitfalls.md` | s50 build script 陷阱 |
| `references/chapter-notes-guide.md` | 章节笔记模板 |
| `references/wikilink-pitfalls.md` | wikilink 陷阱 |
| `references/qa-pitfalls.md` | QA 陷阱 |
| **`references/llm-inference-pitfall.md`** (新增) | **LLM 跨书内容污染防控 (D0 数据缺失约束)** |
