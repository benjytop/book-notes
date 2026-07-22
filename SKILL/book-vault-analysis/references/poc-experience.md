# POC 经验沉淀 (book-vault-analysis-poc-experience)

> 从 `book-vault-analysis-poc-experience` skill 迁移而来 (v1.2.0, 2026-07-21)

## 概述

本文档记录 book-vault-analysis Skill 在 2026-07-20 ~ 2026-07-21 期间的真实运行经验, 包括设计原则, 性能基准, 重建流程等.

## 5 大设计原则 (P1-P5) - 2026-07-21 沉淀

### P1: skill scaffold 创建带占位符模板, LLM 抽取后填入

skill 的 `s50_build_vault.py --phase=scaffold` 创建 MOC + 9 个根目录文件, **包含占位符** (e.g. `(待 LLM 抽取后填入)`). LLM 工作流后, 必须**全部替换**为真实内容. 验证通过 `s95_check_placeholders.py` 硬约束.

### P2: vault 中"不应出现"的 4 类硬规则

任何以下 token 出现在 vault 里 = FAIL:
- `/Users/...` (绝对路径)
- 用户名 (e.g. `<USER>`, `alice`)
- `sources/<书名>.txt` (源文件引用)
- `book-analysis/` (旧 skill 引用)
- `/tmp/` (临时路径)
- `占位`, `已弃用` (placeholder)

### P3: wikilink 必须用 bare stem (`[[X]]`), 不支持路径式 (`[[dir/X]]`)

L1 #10 用 `f.stem` 匹配, 路径式 wikilink 永远不匹配. 目录引用用粗体 `**目录名/**`.

### P4: Mermaid parser 不支持中文 parens

中文 `(`/`)` 在 subgraph 名 或 edge label 里都会解析失败. 用 `-` 替代 (e.g. `父子 (名义)` → `名义父子`).

### P5: phase_moc 不应该覆盖已有完整 MOC

`phase_moc` 只更新 3 段 (`涉及人物` + `章节结构` + `核心概念/主题/摘录`), **不应该清空** 其他段 (豆瓣数据/阅读方式/路径/附录). 早期版本有 bug 已修复.

## 关键经验

### 重建《灿烂千阳》的完整流程 (1分50秒)

```
[0s] 用户: 删除 + 重新生成《灿烂千阳》
[10s] Step 0-2: Pre-flight + Extract (cached /tmp/literary-scratch)
[20s] Step 5: scaffold (skill 自动)
[40s] Step 6: entities (cached /tmp/build_<书名>_partN.py)
[60s] Step 7-8: mermaid + moc (cached scripts)
[70s] Step 9: validate (L1+L2+Placeholder)
[110s] 完成 (验证 PASS)
```

**核心**: `/tmp/literary-scratch/<书名>/spine/` 和 `/tmp/build_<书名>_part{1,2,3}.py` 缓存是**关键加速** (节省 90% 时间).

### 17 本 vault 状态 (2026-07-21)

| 类型 | 数量 |
|---|---|
| 文学 (T1) | 7 (仙症, 灿烂千阳, 追风筝的人, 群山回唱, 遥远的救世主, 天幕红尘, 我人生最开始的好朋友) |
| 思想史 (T2) | 2 (刘擎, 哲学家们都干了些什么) |
| 方法论 (T3) | 2 (卡片笔记, 费曼学习法) |
| 投资 (T4) | 2 (周期, 文明现代化) |
| 商业 (T5) | 1 (纳瓦尔宝典) |
| 政经 (T6) | 1 (美国困局) |
| 混合 (T14) | 2 (局外人, 带一本书去巴黎) |
| 总计 | 17 |

全部 L1+L2+Placeholder PASS.

## 经验教训

### 教训 1: skill 设计阶段不写 /tmp/ 脚本

早期 LLM (我) 习惯性写 `/tmp/build_<书名>_part{1,2,3}.py` 临时脚本. 用户反馈: "我以为把脚本固化到 skill 里的脚本里后就不需要再生成脚本了".

**修复**: skill 的 `s50_build_vault.py` 扩展 `--phase=entities` 接受 `--people-json` 等参数, 让 LLM 生成 JSON 后直接传入, 不需要写脚本.

### 教训 2: 模板占位符要避免硬字符串 "占位"

L1 #8 原本用 `re.compile(r"占位")` 检测, 但实际 vault 用委婉表达 (`(由 LLM 抽取后填入)` / `(待豆瓣数据嵌入后...)`). L1 检测 false-negative.

**修复**: L1 #8 + s95_check_placeholders.py 都扩展到 10 类占位符模式.

### 教训 3: MOC 模板必须包含全部 11 段, 不能只有 4 段

早期 `phase_scaffold` 的 MOC 模板只有 4 段 (书籍信息/章节结构/涉及人物/关系图). LLM 抽取后写的完整 MOC (含豆瓣/阅读方式/摘录/主题/路径/附录 11 段) 被 `phase_moc` 部分覆盖, 导致丢失.

**修复**: scaffold 模板扩展到 11 段, phase_moc 改为只更新 3 段 (人物/章节/概念主题).

### 教训 4: 用户要求路径不要硬编码

PRD 早期硬编码 `/Users/<USER>/...` 路径. 用户反馈: 路径硬编码导致脚本在其他人的机器上无法直接使用, 必须用 token + 示例括号的方式.

**修复**: 路径用 `<VAULT_PARENT>/<书名>/` token + 示例括号, 不硬编码.

## 文件统计

| 类别 | 数量 | 大小 |
|---|---|---|
| `scripts/` | 8 个 Python | ~38K |
| `references/` | 10 个 Markdown | ~28K |
| `templates/` | 14 个 JSON | ~16K |
| `PRD.md` | 1 个 | ~12K |
| `SKILL.md` | 1 个 | ~15K |

## 验证基线

**所有 vault 必须通过**:
- L1 13-POINT 硬检查 (ALL HARD CHECKS PASSED)
- L2 5 项软检查 (hard=0, soft=0)
- Step 9.5 占位符检查 (No unfilled placeholders)
- EPUB hash 一致性 (`md5sum` 比对)

## 下一步

1. 处理剩余书 (如适用)
2. 完善模板自动化 (s95 + s96 进一步独立化)
3. 性能优化 (LLM 抽取可并行化)

---

**原 skill**: `book-vault-analysis-poc-experience` v1.2.0
**迁移日期**: 2026-07-21
**迁移原因**: 清理冗余 skill, 保留知识到主 skill 的 references/