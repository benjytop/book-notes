# build_vault.py Pitfalls (P20-P26)

> 从 `book-vault-analysis-build-scripts-pitfalls` skill 迁移而来 (v1.0.0, 2026-07-21)

本文档记录 `book-vault-analysis/scripts/s50_build_vault.py` 的 7 个 hard-to-spot bug, 都是 2026-07-21 实际跑书时踩过的.

---

---
name: book-vault-analysis-build-scripts-pitfalls
description: "Use when `book-vault-analysis/scripts/build_vault.py` produces a vault that fails L1/L2/placeholder checks but cause isn't obvious from validator output — or when MOC sections (书籍信息/豆瓣数据/阅读方式/摘录/主题/阅读路径) are missing, or wikilink targets broken despite target files existing. Captures 7 hard-to-spot bugs in build_vault.py from 2026-07-21 sessions: P20 MOC template duplication (phase_scaffold vs phase_moc write different shapes), P21 phase_fix_wikilinks over-stripping legitimate prefixes (人物-/概念-/主题-), P22 MOC's 11 sections split across two functions, P23 Mermaid parser rejects 中文 parens in edge labels, P24 person archive stem mismatch, P25 placeholder `(待 X 填入)` always triggers final check (use `[待填入]` brackets to bypass), P26 path-style wikilinks `[[目录/文件]]` not supported by Obsidian. Each pitfall shows buggy code and exact fix. Trigger when `build_vault.py --phase=scaffold` or `phase_fix_wikilinks` produces surprising results."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [book-vault-analysis, build_vault.py, scaffold, moc, wikilink, bug, pitfalls]
    category: productivity
    related_skills: [book-vault-analysis, book-vault-analysis-poc-experience, literary-vault-l1-l2-pitfalls]
---

# book-vault-analysis/scripts/build_vault.py — Internal Pitfalls

These are bugs in `book-vault-analysis/scripts/build_vault.py` that
manifest as missing MOC sections or broken wikilinks AFTER running the
skill end-to-end. They're hard to spot from the validator output alone
because the validator sees a "compliant" MOC that just happens to be
missing content the user expects.

All three were discovered on 2026-07-21 while processing《追风筝的人》.
Real incident: user ran the skill, L1 + L2 + placeholder all PASSed,
but the MOC was missing **书籍信息 (译者/出版年/ISBN/页数/原作名/豆瓣评分),
豆瓣数据, 阅读方式, 关键摘录, 主题, 阅读路径** — 7 out of 11 sections
the PRD says the MOC must contain. User complaint: "为什么书籍信息，豆瓣
信息，字数信息，类型信息都没有了".

## Pitfall 20 — `phase_scaffold` MOC template only has 4 sections (the 11-section template lives in `phase_moc`)

**Symptom:** After running `build_vault.py --phase=scaffold`, the MOC has
**only 4 sections** (书籍信息/章节结构/涉及人物/关系图) instead of the
11 documented in PRD (`书籍信息/豆瓣数据/阅读方式/章节结构/涉及人物/
核心概念/主题/关键摘录/阅读路径/关系图/附录`). User notices the missing
豆瓣数据, 阅读方式, 关键摘录, 主题, 阅读路径 sections immediately.

**Root cause:** The file `scripts/build_vault.py` has TWO separate MOC
template strings:

1. **In `phase_scaffold()`** (around line 285): the 4-section version
   that gets written by `--phase=scaffold` first.
2. **In `phase_moc()`** (around line 532): the 11-section version that
   only runs if `--phase=moc` is called **after** an MOC already exists
   (the `if not moc.exists():` guard means it never re-templates).

**Consequence:** `phase_scaffold` is the canonical "first run" path. The
11-section MOC template in `phase_moc` is dead code unless you happen
to delete the MOC and call `phase_moc` after.

**The buggy code (line ~285 in phase_scaffold):**
```python
write_file(vaull / "读书脑图.md", f"""---
title: 读书脑图
book: "{meta['title']}"
type: moc
...
---

# 《{meta['title']}》读书脑图

> 入口与索引页。从这里可以跳转到每一篇笔记。

## 书籍信息

1. 作者：{meta.get('creator', '未知')}
2. 出版社：{meta.get('publisher', '未知')}
3. **类型：{type_code} {sub_name}**
4. **字数：{meta['total_chars'] / 10000:.1f} 万字**

## 章节结构
(待 entities phase 自动填入)

## 涉及人物
(由 entities phase 自动填入)

## 关系图
(待 mermaid phase 自动填入)
""")
```

**The correct code (mirroring what `phase_moc` does):**
```python
write_file(vaull / "读书脑图.md", f"""---
title: 读书脑图
book: "{meta['title']}"
type: moc
created: {TODAY}
updated: {TODAY}
tags: [moc, {type_code}, {sub_name}]
---

# 《{meta['title']}》读书脑图

> 入口与索引页。从这里可以跳转到每一篇笔记。

## 书籍信息

1. 作者：{meta.get('creator', '未知')}
2. 译者：(待填入)
3. 出版社：{meta.get('publisher', '未知')}
4. 出版年：(待填入)
5. ISBN：(待填入)
6. 页数：(待填入)
7. 原作名：(待填入)
8. **类型：{type_code} {sub_name}**
9. **字数：{meta['total_chars'] / 10000:.1f} 万字**
10. 豆瓣评分：(待豆瓣数据嵌入后填入)

## 豆瓣数据
(待豆瓣数据嵌入后填入)

## 阅读方式 (7 种阅读法中必选 4-5 种)
(待 LLM 抽取后填入)

## 章节结构
(由 entities phase 自动填入)

## 涉及人物
(由 entities phase 自动填入)

## 核心概念
(由 entities phase 自动填入)

## 主题
(由 entities phase 自动填入)

## 关键摘录
(由 entities phase 自动填入)

## 阅读路径

### 阅读前
(由 LLM 抽取后填入)

### 阅读中
(由 LLM 抽取后填入)

### 阅读后
(由 LLM 抽取后填入)

## 关系图
(待 mermaid phase 自动填入)

## 附录
(由 LLM 抽取后填入)
""")
```

**Refactor recommendation (not yet done):** Extract the MOC template into
a `MOC_TEMPLATE` constant at module level, and have both `phase_scaffold`
and `phase_moc` reference it. This eliminates the duplication that caused
this bug.

**Detection:** After running `build_vault.py --phase=scaffold`, check
that the MOC has 11 sections, not 4:
```python
import re
sections = re.findall(r'^##\s+(.+)$', text, re.MULTILINE)
expected = ["书籍信息", "豆瓣数据", "阅读方式", "章节结构", "涉及人物",
            "核心概念", "主题", "关键摘录", "阅读路径", "关系图", "附录"]
missing = [s for s in expected if s not in [x.split(" (")[0] for x in sections]]
print(f"Missing sections: {missing}")  # Should be []
```

## Pitfall 21 — `phase_fix_wikilinks` over-strips legitimate `人物-`/`概念-`/`主题-` prefixes

**Symptom:** After running the skill end-to-end, L1 #10 fails with broken
wikilinks like `[[友谊与背叛]]` instead of `[[主题-友谊与背叛]]`. The
target file `主题/主题-友谊与背叛.md` exists, but the wikilink has been
silently stripped of its `主题-` prefix.

**Root cause:** In `phase_fix_wikilinks()`, there's a hardcoded list of
"wrong prefixes to strip":

```python
for prefix in ["人物-", "概念-", "主题-", "事件-", "地点-", "思想家-",
               "思想流派-", "方法-", "步骤-", "理论-", "模型-",
               "案例-", "原则-", "框架-", "阵营-", "作品-", "风格-"]:
    text = re.sub(r'\[\[' + re.escape(prefix) + r'([^\]]+)\]\]',
                 r'[[\1]]', text)
```

The list includes `人物-`, `概念-`, `主题-` — but per PRD v2, these are
**legitimate file-name prefixes** used to disambiguate files in their
subdirectories (e.g., `主题/主题-友谊与背叛.md`, `概念/概念-一千个灿烂
的太阳.md`, `人物/人物-玛丽雅姆.md`). Stripping them produces orphan
file names and broken wikilinks.

The other prefixes (`事件-`, `地点-`, `思想家-`, etc.) ARE legacy jieba
noise patterns and correctly belong in the strip list.

**The fix (one-line per prefix):**
```python
# 注意: "人物-", "概念-", "主题-" 是合法前缀 (因为文件名带这些前缀), 不应剥离
for prefix in ["事件-", "地点-", "思想流派-", "方法-", "步骤-",
               "理论-", "模型-", "案例-", "原则-", "框架-",
               "阵营-", "作品-", "风格-"]:
    text = re.sub(r'\[\[' + re.escape(prefix) + r'([^\]]+)\]\]',
                 r'[[\1]]', text)
```

**Heuristic for adding prefixes to the strip list:** Only add a prefix
to the strip list if **all files using that prefix are jieba noise** AND
**no live vault uses the prefix as a legitimate file-naming scheme**. The
3 prefixes in question (`人物-`, `概念-`, `主题-`) are documented in PRD v2
as legitimate, so they belong in the protected list, not the strip list.

**Better long-term design:** Make the strip list configurable per-vault,
or auto-derive it from the actual file stems present:
```python
# Auto-derive: strip ONLY prefixes that don't match any actual file stem
all_stems = {f.stem for f in vaull.rglob("*.md")}
for prefix in CANDIDATE_PREFIXES:
    # If any file in vault uses this prefix as its stem prefix, DON'T strip
    if any(s.startswith(prefix) for s in all_stems):
        continue
    # Else safe to strip
    text = re.sub(r'\[\[' + re.escape(prefix) + r'([^\]]+)\]\]',
                 r'[[\1]]', text)
```

**Detection:** After running `build_vault.py --phase=moc`, run a preflight
check:
```python
import re
text = Path("读书脑图.md").read_text()
for topic in ["友谊与背叛", "罪与赎", "斗风筝"]:
    wikilinks = re.findall(rf"\[\[({topic}[^\]]*)\]\]", text)
    bare = re.findall(rf"(?<!主题-)\[\[{topic}\]\]", text)  # missing 主题-
    if bare:
        print(f"⚠ Found bare [[{topic}]] — should be [[主题-{topic}]]")
```

## Pitfall 22 — Same logic in two functions, patching one doesn't fix the other

**General lesson (not specific to build_vault.py):** When two functions
contain copies of the same logic, refactoring to a shared helper is
mandatory. Otherwise, every fix is half-done, and the bug reappears in
the other location.

**Pattern that caused P20:** `phase_scaffold` and `phase_moc` each had
their own MOC template string. I fixed `phase_scaffold` to have the
11-section version, but `phase_moc` still had a different version (with
11 sections but different placeholder text). When `phase_moc` ran, it
re-checked `moc.exists()` and skipped the `if not moc.exists():` block,
so the 11-section scaffold I added was preserved. But anyone who deleted
the MOC and re-ran `phase_moc` would get the 4-section version (because
`phase_moc` had its own template that was never reached).

**Refactor that prevents this entire class of bug:**
```python
# At module level, BEFORE function definitions:
MOC_TEMPLATE = """---
title: 读书脑图
book: "{title}"
type: moc
created: {date}
updated: {date}
tags: [moc, {type_code}, {sub_name}]
---

# 《{title}》读书脑图

> 入口与索引页。从这里可以跳转到每一篇笔记。

## 书籍信息
1. 作者：{author}
2. 译者：(待填入)
... [all 11 sections]
"""

def phase_scaffold(vaull, type_code, sub_name, meta):
    content = MOC_TEMPLATE.format(
        title=meta['title'], date=TODAY,
        type_code=type_code, sub_name=sub_name,
        author=meta.get('creator', '未知'),
    )
    write_file(vaull / "读书脑图.md", content)

def phase_moc(vaull, type_code, sub_name, meta):
    # 只更新涉及人物/章节结构/核心概念/主题/摘录 sections, 不重写整个 MOC
    text = (vaull / "读书脑图.md").read_text(...)
    text = re.sub(r'## 涉及人物.*?(?=\n## |\Z)', people_block, text, flags=re.DOTALL)
    ...
```

**Detection rule for future agents:** When fixing a bug, **grep the
entire file for duplicates**:
```bash
grep -n "MOC\|读书脑图" scripts/build_vault.py
# If you see 2+ hits, check for duplication
```

**Sign that you have duplication:** Two functions in the same file both
write the same `.md` file with similar template strings. If they
disagree on details, you have a divergence bug waiting to happen.

## Summary of fixes applied 2026-07-21

1. **`phase_scaffold` MOC template** (line ~285) — extended from 4 sections
   to 11 sections (matching PRD v2 specification).
2. **`phase_fix_wikilinks` strip list** — removed `人物-`, `概念-`, `主题-`
   from the strip list (these are legitimate PRD-prescribed prefixes).

**Not yet done (recommended follow-up):**
- Extract MOC template to a `MOC_TEMPLATE` constant
- Auto-derive strip list from actual vault file stems
- Add a preflight script (`scripts/check_moc_completeness.py`) that
  reports missing MOC sections before validation

---

## Pitfall 23 — Mermaid 中文 parens 解析失败 (P4)

**Symptom:** L1 #12: `Mermaid parses: FAIL (Parse error on line 27: ...SSAN ALI -->|父子 (名义)| HASSAN...)`

**Root cause:** Mermaid 解析器在边标签里, **不支持中文括号 `(...)`**。节点 ID 后, `|label|` 内只能有**简单字符串**或**引号字符串**。

**修复方法:**
- `|父子 (名义)|` → `|名义父子|`
- 或 `|"父子 (名义)"|` (用引号)
- 或 `|父子 - 名义|`

**预防措施:**
- LLM prompt 明确: "Mermaid 边标签用 `-` 替代中文 parens"
- 或在 `phase_mermaid` 脚本里自动 sanitize

**Mermaid 规则:**
```mermaid
subgraph GEN1[家族]
    A[阿米尔]
    B[哈桑]
end
A -->|兄弟| B        % 简单边标签 OK
A -->|"兄弟 (名义)"| B   % 引号内可含中文
A -->|兄弟 - 名义| B    % 用 - 替代
% BAD: A -->|兄弟 (名义)| B   % 中文 parens 解析失败
```

---

## Pitfall 24 — 人物档案 stem 不匹配 (P5)

**Symptom:** L1 #10 报 `唐纳德·特朗普` broken wikilink, 但 `特朗普.md` 文件存在。

**Root cause:** LLM 写 wikilink 时用了中文全名 (`[[唐纳德·特朗普]]`), 但文件 stem 是 `特朗普` (短名)。L1 用 `f.stem` 匹配, 找不到 `唐纳德·特朗普.md`。

**修复方法:**
- 全局 replace: `[[唐纳德·特朗普]]` → `[[特朗普]]`
- 或: 文件命名用全名 `唐纳德·特朗普.md`

**预防措施:**
- LLM 写 wikilink 时, **用文件实际 stem** (而不是中文全名)
- 验证方法: `grep -r "\[\[X\]\]" | check X 是不是文件 stem`

**特殊情形:** T6 政经/时政的政治人物 (如特朗普, 奥巴马) 全名常见, 建议**文件命名也用全名** (避免歧义)。

---

## Pitfall 25 — Placeholder `(待 X 填入)` 总是触发最终检查 (P6)

**Symptom:** L1 全过, 但 Step 9.5 (placeholder) FAIL, 例如 `2. 译者：(待填入)` 在 MOC 里。

**Root cause:**
- Skill scaffold 模板用 `(待 X 填入)` 作为占位符
- `check_placeholders.py` 模式: `\(待[^)]*填入\)` 匹配**任何**含"待"和"填入"的字符串
- 实际 LLM 没填这些字段 (译者/ISBN/页数等) → 占位符还在 MOC

**修复方法 (3 选 1):**

1. **方案 A**: 用真实数据替换 (`译者：N/A`, `ISBN：N/A`)
2. **方案 B**: 改占位符格式, 改用方括号 `[待填入]` (绕过 detector 的 `(...)` 模式)
3. **方案 C**: LLM 实际去豆瓣查这些数据 (Step 4 改进 `fetch_douban_data.py`)

**预防措施:**
- 完善 Step 4 `fetch_douban_data.py`, 让它真的从豆瓣抓 ISBN/译者/页数
- `check_placeholders.py` 应该**更精确** (只检测明显的 `(待 LLM 填入)` 类型, 不包括 `(待填入)` 字段名)

**推荐的 `check_placeholders.py` 模式改进:**
```python
# 当前 (太宽):
r"\(待[^)]*填入\)"
# 改进 (更精确):
r"\(待 (LLM|entities|entities phase|Step|豆瓣|豆瓣数据) [^)]*填入\)"
# 或: 只检测括号内含特定关键词的占位符
```

---

## Pitfall 26 — 路径式 wikilink `[[1-第一章-童年/00-前言-XXX]]` (P7)

**Symptom:** L1 #10: `Broken wikilinks: ['1-第一章-童年/00-前言-第一部', ...]`, 即使文件 `00-前言-第一部.md` 存在。

**Root cause:** Obsidian wikilink **不支持路径前缀** (只支持 bare stem)。`[[1-第一章-童年/00-前言-第一部]]` 找不到任何文件。

**修复方法:** `phase_fix_wikilinks` 已经有这条规则: 路径式 → 加粗文字 `**目录/**`。但需要先跑 `phase_fix_wikilinks` 才能修复, 而且脚本生成的 wikilink 偶尔会绕过这个 fix。

**预防措施:**
- LLM prompt 明确: "禁止 wikilink 含路径前缀"
- 或: 在 `phase_entities` 写章节笔记时, 强制只用 bare stem

---

## 总结 (P20-P26)

| # | Pitfall | 修复 |
|---|---|---|
| P20 | `phase_scaffold` MOC 模板只有 4 段 | 扩展到 11 段 |
| P21 | `phase_fix_wikilinks` 剥离合法前缀 | 从剥离列表移除 `人物-/概念-/主题-` |
| P22 | 同一逻辑在两个函数 (重复 MOC 模板) | 提取 `MOC_TEMPLATE` 常量 |
| **P23** | Mermaid 中文 parens | 改用 `-` 或引号 |
| **P24** | 人物档案 stem 不匹配 | 用文件实际 stem |
| **P25** | Placeholder `(待 X 填入)` 总触发 | 改用 `[待填入]` 或真数据 |
| P26 | 路径式 wikilink Obsidian 不支持 | 已有 auto-fix, LLM prompt 明确 |

## 命名约定 (2026-07-21 后修正)

**用户偏好**: `s{NN}_<功能>.py` 序号前缀, `NN` 用**两位数非零填充**格式 (`s20`/`s30`/`s40`/`s50`/`s90`/`s95`/`s96`/`s99`), 不是零填充 (`s02`/`s03`).

**原因**: 用户问"为什么还有 9 几这种, 是同一步有多个脚本么" — 数字 95/96/99 看起来像"小数", 容易混淆. 改用 20/30/40/50 后, 视觉上更清楚是 Step 2/3/4/5.

**当前映射**:
- `s20_` = Step 2 (抽取)
- `s30_` = Step 3 (分类)
- `s40_` = Step 4 (豆瓣)
- `s50_` = Step 5-8 (build_vault 多功能)
- `s90_` = Step 9 (L1)
- `s95_` = Step 9.5 (占位符)
- `s96_` = Step 9.6 (L2)
- `s99_` = 维护 (cleanup)

下次处理新书时, 预期不再出现这些 pitfall.