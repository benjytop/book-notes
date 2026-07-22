# L1/L2 校验 Pitfalls 沉淀

> 从 `literary-vault-l1-l2-pitfalls` v1.0.0, `obsidian-vault-validation-pitfalls` v1.0.0, `literary-vor-audit` v1.1.0 三个 skill 合并而来 (2026-07-21)

## Quick Reference: PRD v2 Workflow

10 步工作流 + L1/L2/Placeholder 三层校验:

```
Step 0: Pre-flight         (manual)
Step 1: Identify source     (manual)
Step 2: Extract EPUB        (s20_extract_epub_spine.py)
Step 3: Classify            (s30_classify_book.py)
Step 4: Fetch Douban        (s40_fetch_douban_data.py)
Step 5: Build scaffold      (s50_build_vault.py --phase=scaffold)
Step 6: Extract entities    (s50_build_vault.py --phase=entities)
Step 7: Generate Mermaid    (s50_build_vault.py --phase=mermaid)
Step 8: Update MOC          (s50_build_vault.py --phase=moc)
Step 9: Validate L1         (s90_validate_vault.py)
Step 9.5: Placeholder check (s95_check_placeholders.py)
Step 9.6: Finalize L2       (s96_finalize_vault.py)
```

## L1 Check Map (s90_validate_vault.py)

13-POINT 硬检查:

1. source unchanged (EPUB hash 比对)
2. epub integrity (字节大小)
3. no /Users paths
4. no <USER> (用户名)
5. no sources/X.txt
6. no book-analysis
7. no /tmp/
8. no 外部路径|占位|已弃用
9. no empty/short notes
10. 0 broken wikilinks
11. 0 orphans (BFS from MOC)
12. Mermaid parses (mermaid-cli)
13. Excalidraw (optional)

## L2 Check Map (s96_finalize_vault.py)

5 项软检查 + 1 项硬约束:

1. File-level anomalies (零字节, 异常字符)
2. Frontmatter hygiene (title + type)
3. Network (BFS reachability from MOC)
4. Extra residue scan
5. **Unfilled placeholder residue (HARD)**

## Pitfalls 详解

### Pitfall 8 — 字符级 false positive on 占位/已弃用/外部路径

**症状**: L1 #8 检测失败, 但实际 vault 内容正确.

**原因**: 早期正则只匹配硬字符串 `"占位"`, 但实际 vault 用委婉表达 (e.g. `(由 LLM 抽取后填入)`, `(待豆瓣数据嵌入后...)`).

**修复**: 扩展到 10 类占位符模式, 见 `s95_check_placeholders.py`.

### Pitfall 9 — LLM agent 写 `/tmp/build_<书名>_part*.py` (2026-07-21)

**症状**: LLM (我) 处理新书时, 习惯性写 `/tmp/build_<书名>_part{1,2,3}.py` 临时脚本生成 vault 内容.

**原因**: skill 早期 `s50_build_vault.py` 只支持 scaffold, 没实现 entities phase. LLM 只能手写脚本填充内容.

**修复**:
- `s50_build_vault.py --phase=entities` 接受 `--people-json`, `--concepts-json` 等参数
- `references/entity-extraction-template.md` 提供 7 个 JSON schema

**用户反馈**: "我以为把脚本固化到 skill 里的脚本里后就不需要生成什么脚本了"

### Pitfall 10 — Broken wikilinks

**症状**: L1 #10 报错 "broken wikilink", 但实际文件存在.

**原因**: L1 用 `f.stem` 匹配 wikilink, 不支持:
- 路径式 wikilink `[[目录/文件]]`
- 错误前缀 (e.g. `[[人物-玛丽雅姆]]` vs 文件 `玛丽雅姆.md`)
- 中文括号在 stem (e.g. `[[目录 (X)]]`)

**修复**: `s50_build_vault.py --phase=fix-wikilinks` 自动修复 (去除合法前缀 + 加粗目录引用).

### Pitfall 11 — Orphan notes

**症状**: L1 #11 报错 "orphan", 但 vault 看起来完整.

**原因**: MOC 必须 wikilink 所有 vault 文件, 否则其他文件无法从 MOC BFS 到达 = orphan.

**修复**:
- `s50_build_vault.py --phase=moc` 自动建立 MOC → 人物/章节/概念/主题/摘录 的入链
- 用户填入 MOC 时必须链接所有根文件 (`封面`, `导言-评论`, `无剧透导读` 等)

### Pitfall 12 — Mermaid syntax

**症状**: L1 #12 Mermaid 解析失败.

**原因**: 中文 parens `()` 在 subgraph 名 或 edge label 里无法解析.

**修复**: 用 `-` 或 `_` 替代 (e.g. `父子 (名义)` → `名义父子`).

### Pitfall 13 — Cleanup chain can delete legitimate files (2026-07-20)

**症状**: `s99_cleanup_residue.py` 误删合法文件.

**原因**: 早期版本不跳过 `_backup` 目录, 会扫描备份目录删除.

**修复**: 默认 CWD + 跳过 `_backup` 后缀目录.

### Pitfall 14 — MOC `## 涉及人物`段可能携带 jieba-era prose (2026-07-20)

**症状**: MOC 涉及人物段有自动抽取残留 ("自动抽取 (jieba + co-occurrence, 2026-07-20)").

**修复**: 大模型抽取已替换 jieba, 自动清理残留段.

### Pitfall 15 — Whitespace regex `\\s+` collapse destroys URLs (2026-07-20)

**症状**: vault 中 URL 被替换为单个空格, YAML frontmatter 损坏.

**修复**: 避免 `re.sub(r'\s+', ' ', text)`, 改用 `re.sub(r' +', ' ', text)`.

### Pitfall 16 — `[[目录名]]` doesn't resolve in Obsidian (2026-07-20)

**症状**: 路径式 wikilink `[[目录/文件]]` 在 Obsidian 显示为红色 (broken).

**修复**: 改用粗体 `**目录名/**` 引用, 或纯文本 "目录名/".

### Pitfall 17 — Chinese numerals sort wrong in Obsidian (2026-07-20)

**症状**: 章节文件按 Unicode 排序, 中文数字顺序乱 (一, 七, 三, 九...).

**修复**: 保留阿拉伯数字前缀 `NN-` (e.g. `01-第一章.md`).

### Pitfall 18 — Same filename in multiple subdirs (2026-07-20)

**症状**: L1 检测 `f.stem` 时多个同名文件冲突.

**修复**: 主题文件 `主题-X.md`, 摘录 `摘录-X-Y.md` 加前缀避免冲突.

## Spine chunking for LLM extraction

**单章 spine 过大时**: 切分为多段 (`spine_NNN-part0000.txt`, `spine_NNN-part0001.txt` 等). LLM 抽取时**按 part 顺序读**, 不跨越 part 边界.

## Quick preflight checklist

跑新书前必查:

- [ ] EPUB 路径存在, 大小 > 1KB
- [ ] EPUB hash 已记录 (`md5sum`)
- [ ] /tmp/literary-scratch/<书名>/ 不存在 (或删除)
- [ ] vault 目录不存在 (或确认可覆盖)
- [ ] 分类置信度 ≥ 0.5 (s30 输出)
- [ ] 豆瓣 ISBN 已知 或 兜底搜索可用
- [ ] build_vault.py type 参数已知 (T1-T14)

## 12-point audit (literary-vor-audit)

**HARD Category** (MUST_FIX before publishing):
1. /Users/<USER> 路径泄漏
2. 用户名泄漏
3. 源文件引用 (sources/X.txt)
4. book-analysis 等废弃 skill 引用
5. /tmp/ 临时路径
6. 占位符 / 已弃用
7. 空文件 / 过短文件
8. broken wikilinks
9. orphans (无入链)
10. Mermaid 解析失败
11. EPUB hash 不匹配
12. 硬规则 (绝对路径等)

**SHOULD_FIX**:
- Frontmatter 不完整
- 长段落 (> 8 行)
- 跨章节重复内容
- 引文改写

**NOTE_ONLY** (publishable, but worth telling the user):
- 字数偏差 ± 10%
- 豆瓣评分缺失
- 短评 < 3 条

## Severity rules

| 严重级别 | 描述 | 处理 |
|---|---|---|
| HARD | 阻塞 publish | 必须修复 |
| SHOULD_FIX | 影响质量 | 建议修复 |
| NOTE_ONLY | 信息提示 | 可忽略 |

---

**原 skills**:
- `literary-vault-l1-l2-pitfalls` v1.0.0
- `obsidian-vault-validation-pitfalls` v1.0.0
- `literary-vor-audit` v1.1.0

**迁移日期**: 2026-07-21
**迁移原因**: 清理冗余 skill, 合并知识到主 skill 的 references/

## 隐私 + 路径清理 (来自 obsidian-vault-build/privacy-and-path-scrub.md)

vault 是用户**打开 Obsidian 阅读**的内容, 不应该是会话日志. 必须清理:

- **绝对文件系统路径** (`/Users/<user>/...`)
- **源文件夹引用** (`sources/<file>.txt`, `book-analysis/...`)
- **用户名** (e.g. `<USER>`, `alice`, `bob`)
- **占位符残留** (`[已弃用：外部路径]` 等)

**原因**:
- 泄漏主机名/OS 用户名 → 隐私问题
- 源文件夹路径 → vault 不再自包含, 用户要维护第二个文件夹
- 占位符残留 → 视觉噪音

**实现**: 已固化到 L1 #3-#8 硬检查, 不需要手动 pass.

---

