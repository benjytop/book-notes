# Placeholder Residue 检测 (Placeholder Detection)

## 概述

本检查项检测 vault 中**未替换的占位符**。这是流程成熟度的关键校验:

- **中间过程 (skill scaffold)**: 可以有占位符 (模板待填充)
- **最终 vault (finalize_vault)**: **不能**有任何占位符

## 占位符模式 (10 类)

### 1. Skill 模板占位符 (新式)

| 模式 | 示例 | 来源 |
|---|---|---|
| `(待 X 填入)` | `(待 LLM 抽取后填入)` | skill scaffold |
| `(待 X 抽[取] .* 填入)` | `(待 entities phase 自动填入)` | skill scaffold |

### 2. 老式占位符 (历史遗留)

| 模式 | 示例 |
|---|---|
| `(由 LLM...填入)` | `(由 LLM 抽取后填入)` |
| `(由 [Ll][Ll][Mm] ... 填入)` | `(由 llm 内容生成填入)` |
| `(由 X 填入)` | `(由 author_intro 填入)` |
| `(由 Step X 填入)` | `(由 Step 8 填入完整内容)` |
| `(Step X 填入)` | `(Step 6 填入 51 章 wikilink 列表)` |

### 3. 豆瓣占位符

| 模式 | 示例 |
|---|---|
| `(由 douban 填入)` | `(由豆瓣 author_intro 填入)` |
| `(由 content_intro 填入)` | `(由豆瓣 content_intro 填入)` |
| `(由 douban 填入)` | `(由 douban author_intro 填入)` (i 模式) |

## 实现

### 在 s96_finalize_vault.py 中

```python
def check_unfilled_placeholders(md_files: list[Path]) -> dict:
    """检测 vault 中是否有未替换的占位符."""
    PATTERNS = [
        re.compile(r"\(待[^)]*填入\)"),
        re.compile(r"\(由\s*[Ll][Ll][Mm][^)]*填入\)"),
        re.compile(r"\(由\s*[\u4e00-\u9fff]+\s*[Ff]illin?\)"),
        re.compile(r"\(由\s*[Ss]tep\s*\d+[^)]*填入\)"),
        re.compile(r"\(Step\s*\d+\s*填入[^)]*\)"),
        re.compile(r"\(由[^)]*author_intro[^)]*填入\)"),
        re.compile(r"\(由[^)]*content_intro[^)]*填入\)"),
        re.compile(r"\(由[^)]*douban[^)]*填入\)", re.IGNORECASE),
        re.compile(r"\(LLM\s*内容生成填入\)"),
    ]

    findings = []
    for f in md_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.split("\n"), 1):
            for pattern in PATTERNS:
                if pattern.search(line):
                    findings.append({
                        "file": str(f.relative_to(...)),
                        "line": line_no,
                        "content": line.strip()[:80],
                    })
                    break
    return findings
```

### 计入 hard_issues

```python
hard_issues = (
    ...
    + len(placeholders)  # 占位符未替换 = 硬 issue
)
```

## 工作流位置

### Step 5: scaffold → 创建模板 (允许占位符)
- skill 创建 `(待 X 填入)` 模板
- validator L1 #8 检测到占位符 → FAIL (但这只是中间状态)

### Step 6: entities → LLM 填充内容
- LLM 抽取实体, 写入真实内容
- 占位符被替换

### Step 8: moc → 更新 MOC
- MOC 完整化, 包含所有 wikilink

### Step 9.5: placeholder-detection → 全局校验
- 检测所有占位符
- 如果发现 → FAIL + 列出文件:行号

### Step 9.6: finalize_vault → 软检查
- 4 类软检查 (file_anomalies, frontmatter, network, residue)
- 输出最终报告

## 输出格式

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

## 使用方法

### 直接调用 s96_finalize_vault.py

```bash
python3 scripts/s96_finalize_vault.py <vault_path>
```

输出包含 5 个检查项 (1-5), 其中 #5 是 placeholder detection。

### 单独调用

```bash
python3 scripts/s95_check_placeholders.py <vault_path>
```

输出仅 placeholder 检测结果。

## 设计意图

**为什么需要这个检查**:

1. **流程完整性**: 中间过程的占位符必须在最终 vault 中被替换
2. **可读性**: 最终 vault 中的 `(待 X 填入)` 严重影响 Obsidian 阅读体验
3. **质量保证**: 防止"半成品" vault 被发布

**为什么不在 Step 9 (L1) 检测**:

- L1 是**硬约束**检查 (wikilink, orphan, mermaid parses 等)
- 占位符是**流程成熟度**检查
- 应该作为**独立的检查项** (`[5] Unfilled placeholder residue`)

**为什么不禁止中间过程的占位符**:

- skill scaffold 需要占位符作为模板
- LLM 抽取需要知道要填充什么
- 禁止占位符会让 scaffold 流程难以调试

## 最佳实践

1. **skill scaffold 阶段**: 放心用占位符
2. **LLM 抽取阶段**: 主动替换占位符 (用 `substitute_placeholder()` 工具)
3. **finalize 阶段**: 严格检查, 不留占位符
4. **修复循环**: 根据 validator 输出定位具体文件:行号

## 修复方法

### 手动修复

```bash
# 找到所有占位符
grep -rn "(待\|(由\|(Step\|(LLM" <vault_path>/*.md

# 删除或替换
```

### 自动修复

```python
# 用占位符替换为真实内容
for f in vault.rglob("*.md"):
    text = f.read_text()
    text = text.replace("(待 X 填入)", "实际内容")
    f.write_text(text)
```

## 性能

| vault 大小 | 检测耗时 |
|---|---|
| 100 .md | < 1s |
| 500 .md | ~2s |
| 1000 .md | ~5s |

## 已知限制

- **正则误判**: 如果真实内容恰好包含占位符模式 (如 `"(待办)"` 含 "(待"), 会被误判
  - **缓解**: 用 `[\u4e00-\u9fff]+填入` 精确匹配
- **跨行占位符**: 当前只检测单行
- **Mermaid 内部**: mermaid 块内的 `(...)` 不应该被检测 (但当前会)
  - **缓解**: 检查前排除 `mermaid` 代码块