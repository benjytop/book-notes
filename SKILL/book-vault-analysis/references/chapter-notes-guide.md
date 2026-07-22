# 章节笔记指南 (Chapter Notes)

> 从 `obsidian-vault-chapter-notes` skill 迁移而来 (v1.0.0, 2026-07-21)

## 来源 references
- `references/wikilink-pitfalls.md` (10 wikilink pitfalls)
- `references/2026-07-20-update.md` (session update)

---

## SKILL.md 主体内容

# Obsidian Vault Chapter Notes (Level 2 Depth)

## Overview

This Skill captures **per-chapter note generation for literary book vaults** at the
depth and structure the user verified in 2026-07-20. Two problems it solves:

1. **Hollow chapter notes** — the previous default of "one file per Part"
   produced 25-line skeleton notes that the user called out as "空"
   (empty). The fix is one file per chapter with **Level 2 depth**:
   6 required sections (场景 / 关键事件 / 关键引用 / 人物 / 主题 / 与其他章的连接).

2. **Obsidian file tree sorting chaos** — Chinese numeral filenames sort
   lexicographically wrong (`第一章`, `第七章`, `第三十一章`, `第十七章`, ...
   instead of 1, 2, 3). The fix is Arabic-numeral prefix (`01-第一章.md`,
   `02-第二章.md`) and per-directory unique suffixes for foreword files
   (`00-前言-玛丽雅姆.md` vs `00-前言-莱拉.md`).

## When to Use

Use this Skill when:

- Generating per-chapter notes for a literary book vault (any long novel)
- The current `章节/` directory contains only skeleton notes (25 lines each)
- User complains about Obsidian file tree sorting (`这里面排序非常乱`)
- User asks "如何定义这个章节的内容丰富度" (how to define chapter depth)

Do NOT use this Skill:

- For the initial vault scaffold (use `literary-zh-analysis` first)
- For short story collections where one file per story is enough granularity

## Granularity Decision Matrix

| Granularity | When | Cost | Example |
|---|---|---|---|
| **A. Per-part** | 短篇集 / 散文集, 不需要逐章细读 | ~6 files | 《仙症》(8 短篇) |
| **B. Per-chapter (default)** | **长篇小说** | 51 files for 《灿烂千阳》 | 《追风筝的人》《灿烂千阳》《天幕红尘》 |
| **C. Per-chapter + cross-references** | 关键章做精读笔记 | 51+ files | overkill |

## Level 2 Chapter Format

Each chapter file MUST contain 6 sections:

```markdown
---
title: "第X章"
book: "<书名>"
chapter: "01-第一章"
type: chapter
created: <date>
updated: <date>
tags: [chapter, <书名>, <作者>]
source: "源文本（按 spine 顺序）"
---

# 第X章

## 场景

- (3-5 个场景, 每个 1 行: 地点 + 情节 + 人物)

## 关键事件

1. (按时间或重要性的 5-10 个事件)

## 关键引用

> (3-5 条原文金句, 用 markdown blockquote)

## 人物

- [[人物名]] (本章出场)
- [[人物名]]

## 主题

- (本章核心探讨的 2-4 个主题)

## 与其他章的连接

(200 字以内的跨章连接: 人物/事件/主题如何前后呼应)
```

## File Naming Pattern (Obsidian Sortable)

```
章节/
├── 00-封面.md
├── 01-导言-评论.md
├── 1-第一部-玛丽雅姆/                 ← 1-/2-/3-/4- prefix for dir sort
│   ├── 00-前言-玛丽雅姆.md            ← unique suffix per part
│   ├── 01-第一章.md
│   ├── 02-第二章.md
│   ...
│   └── 15-第十五章.md
├── 2-第二部-莱拉/
│   ├── 00-前言-莱拉.md
│   ├── 16-第十六章.md
│   ...
├── 3-第三部-阿富汗的命运/
│   ├── 00-前言-阿富汗.md
│   ├── 27-第二十七章.md
│   ...
├── 4-第四部/
│   ├── 00-前言-尾声.md
│   ├── 48-第四十八章.md
│   ├── 52-后记.md
│   ├── 53-致谢.md
│   ├── 54-附录.md
│   ├── 55-译后记.md
│   └── 56-版权.md
```

### Why this works

- **Arabic numeral prefix** (`01-`, `02-`) sorts correctly in Obsidian
  (which uses lexicographic order). Chinese numerals `第十章` sort wrong.
- **`00-前言-XXX.md`** sorts to top of each part directory. Each part gets
  a unique suffix (`-玛丽雅姆`, `-莱拉`, `-阿富汗`, `-尾声`) so the L1
  validator doesn't flag 3 of 4 as orphans (same stem collision).
- **`1-/2-/3-/4-` directory prefix** sorts parts in reading order in
  Obsidian's file tree.

### Wikilink consequence

All wikilinks in MOC, 章节地图, and other files MUST use the full stem:

```markdown
[[01-第一章]]      ← matches 01-第一章.md
[[第一章]]         ← BROKEN (no file with this exact stem)
```

When chapter files are renamed (e.g., to add NN- prefix), run a sweep
to update all wikilinks:

```python
import re
from pathlib import Path
RENAMES = {"第一章": "01-第一章", "第二章": "02-第二章", ...}
for f in Path(VAULT).rglob("*.md"):
    text = f.read_text(encoding="utf-8")
    for old, new in RENAMES.items():
        text = re.sub(r"\[\[" + re.escape(old) + r"\]\]", f"[[{new}]]", text)
    f.write_text(text, encoding="utf-8")
```

## MOC Update Pattern

Replace the single "6 章节 = 封面 + 导言 + 3 部 + 尾声" table with a
detailed per-chapter listing:

```markdown
## 章节结构 (51 章 + 4 部 + 附录)

### 第一部: 玛丽雅姆 (1959-1978, 15 章)

| 章 | 标题 | 主题 |
|---|---|---|
| [[00-前言-玛丽雅姆]] | 第一部前言 | 概述 |
| [[01-第一章]] | 5 岁的"哈拉米" | 私生女身份 |
...
| [[15-第十五章]] | 1978 年的邻居 | 政治动荡开端 |

### 第二部: 莱拉 (1987-1994, 11 章)

| 章 | 标题 | 主题 |
|---|---|---|
| [[00-前言-莱拉]] | 第二部前言 | 概述 |
| [[16-第十六章]] | 1987 年的春天 | 莱拉童年 |
...
```

This makes every chapter a clickable wikilink from the MOC.

## Directory References

`[[目录名]]` doesn't resolve in Obsidian. Use bold + slash for directory
references:

```markdown
- 详见 **1-第一部-玛丽雅姆/** 中的 [[01-第一章]]
- 在 **4-第四部/** 目录下
```

The L1 validator accepts `[[目录名]]` as valid (it tracks folder_names),
but Obsidian will not — this is a real bug in L1's logic, but we work around
it by using the bold + slash notation.

## Appendix Files

Special chapters (后记/致谢/附录/译后记/版权) live at vault root level
(not in any part directory) and use sequential numeric prefix continuing
from the last chapter:

```
章节/52-后记.md
章节/53-致谢.md
章节/54-附录.md
章节/55-译后记.md
章节/56-版权.md
```

## Verification After Chapter Generation

After running chapter generation, **must** re-run L1 + L2:

```bash
cd ${VAULT}
python3 ~/.hermes/skills/productivity/literary-zh-analysis/scripts/validate_vault.py "<书名>"
python3 ~/.hermes/skills/productivity/literary-zh-analysis/scripts/finalize_vault.py "<书名>"
```

Both must show:
- L1: `ALL HARD CHECKS PASSED`
- L2: `hard = 0  soft = 0`

### Common pitfalls after Step 8

| L1/L2 Check | Symptom | Fix |
|---|---|---|
| L1 #10 | `[[第N章]]` (no NN- prefix) doesn't match `NN-第N章.md` | Sweep script above |
| L1 #11 | Each `00-前言-XXX.md` must have explicit MOC inbound | Add to `### 部前言` section |
| L1 #12 | Mermaid still parses fine (chapter notes don't touch it) | n/a |
| L2 #2 | Whitespace-collapse bugs from earlier cleanups | See literary-vault-l1-l2-pitfalls Pitfall 15 |

## Worked Example: 《灿烂千阳》POC (2026-07-20)

| Input | Value |
|---|---|
| Book | 《灿烂千阳》 (A Thousand Splendid Suns) |
| Author | [美] 卡勒德·胡赛尼 |
| Type | 文学 (literary) |
| Chapters | 51 章 + 4 部前言 + 5 附录 = 60 章节元素 |
| Time | ~17 minutes |
| Result | L1: ALL HARD CHECKS PASSED, L2: hard=0 soft=0 |

## Cost Estimate Per Book

| Book | Chapters | Est. time |
|---|---|---|
| 《仙症》 (8 短篇) | 8 | ~5 min |
| 《局外人》 | 5 + 哲学部分 | ~10 min |
| 《天幕红尘》 | 24 | ~12 min |
| 《灿烂千阳》 | 51 | ~17 min |
| 《追风筝的人》 | 25 | ~12 min |
| 《遥远的救世主》 | 24 | ~12 min |
| 《带一本书去巴黎》 | ~20 | ~12 min |
| 《我人生最开始的好朋友》 | 散文集, ~12 | ~10 min |
| 《哲学家们都干了些什么》 | 杂文, 思想史 | ~12 min |
| 《纳瓦尔宝典》 | 短文集 | ~10 min |
| 《周期》 | 12 投资章 | ~12 min |

## Related Skills

- `literary-zh-analysis` — main vault scaffold (this Skill extends it with chapters)
- `type-aware-entity-extraction` — entity layer (人物/概念/事件)
- `literary-vault-l1-l2-pitfalls` — Pitfall 16/17/18 cover the underlying validator quirks
- `` — generic Obsidian vault patterns