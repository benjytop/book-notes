# L2 验证规则 (4-class 软检查)

`s96_finalize_vault.py` 跑 4 类软检查。

## 检查项清单

| # | 检查 | 实现 |
|---|---|---|
| 1 | File-level anomalies | 文件名/编码/异常字符 |
| 2 | Frontmatter hygiene | 所有 .md 有 `title` 和 `type` |
| 3 | Wikilink reachability | 所有 .md 能从 MOC BFS 到达 |
| 4 | Extra residue scan | 残留 token (占位/已弃用等) |

## 关键实现

### Check #1: File-level anomalies

- 文件名异常字符
- 编码错误 (非 UTF-8)
- 文件名长度异常
- 空文件

### Check #2: Frontmatter hygiene

```yaml
---
title: <name>           # required
type: character | ...    # required
created: 2026-07-20
updated: 2026-07-20
tags: [<type>, ...]
---
```

每个 .md 必须有 `title` + `type`。否则标记为 `missing title`。

### Check #3: Wikilink reachability

**BFS from MOC**:
```python
def bfs_reachable(moc_path, all_files):
    visited = {moc_path}
    queue = [moc_path]
    while queue:
        current = queue.pop(0)
        for target in extract_wikilinks(current):
            if target in all_files and target not in visited:
                visited.add(target)
                queue.append(target)
    return visited
```

任何不在 `visited` 集合中的文件都是 unreachable (orphan-like)。

### Check #4: Extra residue scan

扫描 .md 文件是否含有:
- `占位` (placeholder)
- `已弃用` (deprecated)
- `TODO` / `FIXME` / `XXX`
- `calibre` (calibre 软件残留)
- `外部路径`

## L2 输出格式

```
SUMMARY  ::  hard = N  soft = M
```

- `hard = 0` 必须满足
- `soft` 是警告, 可接受

## 调用方法

```bash
cd <vault_root>
python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/s96_finalize_vault.py "<书名>"
```
