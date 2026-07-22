# L1 验证规则 (13-POINT Hard Checks)

`s90_validate_vault.py` 跑 13-POINT 硬检查 + 2 项加项。

## 检查项清单

| # | 检查 | 实现 |
|---|---|---|
| 1 | source unchanged | 比较 EPUB md5 (Pre-flight 记录 vs 当前) |
| 2 | epub integrity | 验证 EPUB 文件可正常打开 |
| 3 | no /Users paths | grep `/Users/[A-Za-z]` 模式 |
| 4 | no <USER> | grep `\b<USER>\b` (case-insensitive) |
| 5 | no sources/X.txt | grep `sources/\w+\.txt` |
| 6 | no book-analysis | grep `book-analysis` |
| 7 | no /tmp/ | grep `/tmp/` |
| 8 | no 外部路径/占位/已弃用 | grep 三个关键词 |
| 9 | no empty/short notes | 文件 < 50 chars 标记为 short |
| 10 | 0 broken wikilinks | `[[X]]` 必须指向存在的 .md 文件 |
| 11 | 0 orphans | 每个 .md 必须被 MOC 链入 |
| 12 | Mermaid parses | 调用 mermaid-cli 渲染验证 |
| 13 | Excalidraw parses | (optional) |
| (+) | prefix compliance | 章节/子目录有 NN- 前缀 |
| (+) | root no NN- prefix | 根目录文件不需 NN- 前缀 |

## 关键实现

### Wikilink 匹配 (check #10)

`validator` 用 `f.stem` (无 .md) 作为目标匹配:

```python
note_names = set()
for f in vault.rglob("*.md"):
    note_names.add(f.stem)
```

**重要规则**:
- ✅ `[[00-前言-第一部]]` → 匹配 `00-前言-第一部.md`
- ❌ `[[1-第一部-玛丽雅姆/00-前言-第一部]]` → **不匹配** (路径前缀, L1 不支持)
- ❌ `[[前言]]` (无前缀) → 不匹配 `00-前言-XXX.md`

**所有 wikilink 必须用 `[[bare-stem]]` 格式**。

### Orphans 检测 (check #11)

```python
orphans = set(note_names) - set(counts.keys())
```

任何不在 MOC 链入的 .md 文件都是 orphan。

**修复方法**: 在 MOC 中加 `[[orphan-file]]` 链接。

### Mermaid Parsing (check #12)

调用 `mermaid-cli` 渲染 `<mermaid>` 块:

```bash
npx -y -p @mermaid-js/mermaid-cli@latest mmdc \
  -i /tmp/mermaid-input.mmd -o /tmp/mermaid-output.svg --quiet
```

如果失败 (e.g., Chinese parens in subgraph), 报错。

## L1 失败处理流程

```
L1 FAIL
↓
查看具体错误 (broken/orphan/prefix)
↓
定位文件: grep "broken_target" *.md
↓
修复: 自动生成正确 wikilink, 添加 inbound
↓
重新运行: s90_validate_vault.py
↓
PASS → 继续
```

**关键**: 不要在修复循环中手写 wikilink, 让 `s50_build_vault.py` 自动生成。

## 调用方法

```bash
cd <vault_root>
python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/s90_validate_vault.py "<书名>"
```

`书名` 是 vault 的子目录名 (e.g., `灿烂千阳`)。
