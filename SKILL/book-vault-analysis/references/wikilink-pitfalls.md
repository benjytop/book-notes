# Wikilink Pitfalls (10 关键陷阱)

> 从 `obsidian-vault-chapter-notes/references/wikilink-pitfalls.md` 迁移而来

---

# Wikilink Pitfalls in Obsidian Vault Validation (Critical 2026-07-20 Lessons)

This is the consolidated pitfalls file covering the **10-minute broken-wikilink debugging cycle** we hit when processing《灿烂千阳》. These pitfalls apply to any literary/non-fiction book vault, not just chapters.

## Why this matters

L1 validator's `note_names = {f.stem for f in vault.rglob("*.md")}` uses **exact filename stem** to resolve wikilinks. Obsidian uses **vault-wide fuzzy search** to resolve wikilinks. These are NOT the same. L1 is stricter than Obsidian. What works in Obsidian may fail L1.

The 10-minute debugging cycle happened because we had 3 layers of wikilink formatting issues simultaneously. This file documents each layer and the fix.

## Pitfall 1: Wikilink prefix must match actual filename

**Symptom**:
```
L1 #10 FAIL: 23 unique: ['00-前言-尾声', '00-前言-玛丽雅姆', '00-前言-莱拉', ...]
```

**Cause**: The MOC has `[[主题-阿富汗女性的双重压迫]]` but the file is at `主题/主题-阿富汗女性的双重压迫.md`. Wait, that should work. The actual issue was: the MOC had `[[阿富汗女性的双重压迫]]` (no prefix) but the file was `主题-阿富汗女性的双重压迫.md` (with prefix).

**Fix**: Always match the wikilink text **exactly** to `f.stem` (no path, no extension).

```python
# Right
text = "[[主题-阿富汗女性的双重压迫]]"  # matches "主题-阿富汗女性的双重压迫.md"

# Wrong
text = "[[阿富汗女性的双重压迫]]"  # no such stem
text = "[[主题/主题-阿富汗女性的双重压迫]]"  # L1 doesn't parse path-style
```

**Best practice**: Auto-generate all wikilinks via script, never hand-write. The `[[X]]` is always exactly `f.stem`.

## Pitfall 2: Directory names cannot be wikilink targets

**Symptom**:
```
L1 #10 FAIL: ['1-第一部-玛丽雅姆', '2-第二部-莱拉', '3-第三部-阿富汗的命运', '4-第四部']
```

**Cause**: MOC referenced `[[1-第一部-玛丽雅姆]]` hoping it would resolve to the directory. L1 uses `f.stem` which only matches **files**, not directories.

**Fix**: Use bold + slash for directory references:
```markdown
详见 **1-第一部-玛丽雅姆/** 中的 [[00-前言-玛丽雅姆]]
```

Don't use `[[目录名]]` ever.

## Pitfall 3: Don't write "path-style" wikilinks

**Symptom**:
```
L1 #10 FAIL: ['1-第一部-玛丽雅姆/00-前言-玛丽雅姆', ...]
```

**Cause**: Some tools (and some writers) use `[[dir/file]]` format. L1 doesn't parse slashes in wikilink target.

**Fix**: Use bare stem only, not path:
```python
# Right
text = "[[00-前言-玛丽雅姆]]"  # matches 1-第一部-玛丽雅姆/00-前言-玛丽雅姆.md

# Wrong
text = "[[1-第一部-玛丽雅姆/00-前言-玛丽雅姆]]"  # slashes not supported
```

## Pitfall 4: Unique stem across all .md files

**Symptom**:
```
L1 #11 FAIL: 1 files: ['00-前言']
```

**Cause**: 4 files all named `00-前言-XXX.md` (one per part) all share the prefix `00-前言-`. But the actual stems are different (`00-前言-玛丽雅姆`, `00-前言-莱拉`, etc.) so this is fine. However, if you have a generic `00-前言.md` and specific `00-前言-XXX.md` files, the generic one becomes orphan.

**Fix**: Make all 4 foreword files use unique suffixes. The convention used in 《灿烂千阳》:
- `1-第一部-玛丽雅姆/00-前言-玛丽雅姆.md`
- `2-第二部-莱拉/00-前言-莱拉.md`
- `3-第三部-阿富汗的命运/00-前言-阿富汗.md`
- `4-第四部/00-前言-尾声.md`

Each has a unique stem. None collide.

## Pitfall 5: Orphan detection requires MOC inbound

**Symptom**:
```
L1 #11 FAIL: 55 files: ['00-封面', '01-导言-评论', '前言-玛丽雅姆', '第一章', ...]
```

**Cause**: Every .md file (except the MOC) must be linked from MOC or reachable via BFS from MOC. The validator checks `set(note_names) - set(counts.keys())` where `counts` is the dict of wikilink targets found in the corpus.

**Fix**: For each new file type, add a MOC section that lists them:

```markdown
## 涉及人物
- [[玛丽雅姆]] (主角 A)
- [[莱拉]] (主角 B)
...

## 关键摘录
- [[摘录-01-娜娜的遗言]]
- [[摘录-02-玛丽雅姆的最后]]
...

## 关键人物档案 (出版关系)
- [[卡勒德·胡赛尼]]
- [[李继宏]]
- [[上海人民出版社]]
- [[世纪文景]]
```

## Pitfall 6: shutil.move loses .md extension

**Symptom**:
```
ls /path/to/file.md  →  file  (no .md)
```

**Cause**: When renaming files via `shutil.move(src, dst)`, if `dst` doesn't include the .md extension, the extension is dropped. This is a Python pathlib gotcha.

**Fix**: Always include .md in the destination:
```python
import shutil
from pathlib import Path

old = Path("chapters/00-前言-玛丽雅姆.md")
new = Path("chapters/00-前言-第一部.md")
shutil.move(str(old), str(new))  # works, keeps .md

# Don't do this
new_bad = Path("chapters/00-前言-第一部")  # no .md
shutil.move(str(old), str(new_bad))  # silently renames without .md
```

If you accidentally drop the extension, fix immediately:
```python
if not new.with_suffix('.md').exists() and new.exists():
    new.rename(new.with_suffix('.md'))
```

## Pitfall 7: cleanup_residue.py must skip backups

**Symptom**: Running cleanup accidentally deletes jieba residue from `_backup` directories.

**Cause**: cleanup loops over all subdirectories in CWD. If user has a backup dir like `golden_xxx_backup/`, the script will clean it too.

**Fix**: Skip directories with `backup` in the name:
```python
if "_backup" in vault.name.lower() or "backup" in vault.name.lower():
    continue
```

## Pitfall 8: When refactoring wikilink formats, do it in one pass

**Symptom**: A wikilink cleanup script (e.g., removing `人物-` prefix) leaves the body wikilinks mismatched with the file names.

**Fix**: When renaming files:
1. First, sweep all body files to update their wikilinks
2. Then, rename the files
3. Then, run L1 + L2 to verify

The other order leaves broken links:
```python
# Wrong order
old_files = ["人物-玛丽雅姆.md"]
new_files = ["玛丽雅姆.md"]
# Step 1: rename files
for old, new in zip(old_files, new_files):
    shutil.move(...)
# Step 2: wikilinks still say [[人物-玛丽雅姆]] → broken
```

```python
# Right order
# Step 1: update wikilinks first
for f in vault.rglob("*.md"):
    text = f.read_text(encoding="utf-8")
    text = text.replace("[[人物-玛丽雅姆]]", "[[玛丽雅姆]]")
    f.write_text(text, encoding="utf-8")
# Step 2: rename files
shutil.move(...)
```

## Pitfall 9: L1 broken/orphan reports may be "stale"

**Symptom**: After fixing one issue, the next L1 run still shows the old broken list.

**Cause**: Validator output is generated at the moment of script execution, not cached. So this shouldn't happen, but make sure you're running L1 fresh, not from a buffer.

**Fix**: Always re-run L1 after each fix:
```bash
python3 scripts/validate_vault.py "灿烂千阳" 2>&1 | tail -10
```

## Pitfall 10: First 3 cleanup rounds may not be enough

**Symptom**: After running cleanup_residue.py, L1 still shows broken wikilinks.

**Cause**: Cleanup removes jieba-files but doesn't fix the wikilinks that referenced them. L1 then shows the broken wikilinks.

**Fix**: After cleanup, run the wikilink sweep:
```python
# After cleanup, sweep broken wikilinks (replace with plain text)
import re
all_stems = {f.stem for f in vault.rglob("*.md")}
for f in vault.rglob("*.md"):
    text = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', text):
        target = m.group(1).strip()
        if target not in all_stems:
            text = re.sub(r'\[\[' + re.escape(target) + r'\](\|[^\]]+)?\]', target, text)
    f.write_text(text, encoding="utf-8")
```

## Quick Reference Table

| Mistake | Detection | Fix |
|---|---|---|
| `[[X]]` references `X-Y.md` | L1 #10 broken wikilinks | Add `-Y` prefix to wikilink text |
| `[[目录名]]` | L1 #10 broken wikilinks | Use bold + slash instead |
| `[[1-第一章/00-前言]]` path-style | L1 #10 broken wikilinks | Use bare stem `[[00-前言-第一部]]` |
| `00-前言.md` in multiple dirs | L1 #11 orphan | Unique suffix per dir |
| File renamed but body wikilinks not | L1 #10 broken | Sweep wikilinks before rename |
| shutil.move drops .md | Files lack extension | Include .md in dst, fix immediately |
| cleanup nukes backup | User notices data loss | Skip dirs with "backup" in name |

## Validation Workflow After Any Change

```bash
# 1. Validate
cd <vault_root>
python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/validate_vault.py "<书名>" 2>&1 | tail -10

# 2. If broken, grep for specific targets
python3 -c "
import re, subprocess
r = subprocess.run(['python3', '.../validate_vault.py', 'X'], capture_output=True, text=True, cwd='<vault_root>')
m = re.search(r'Broken wikilinks \(\d+\):\n((?:  - [^\n]+\n)+)', r.stdout)
if m: print(m.group(1))
"

# 3. Locate broken wikilinks in source files
grep -rn "目标名" <vault_root> --include="*.md"

# 4. Fix and re-validate
```

## Cost of This Debugging Cycle

On 2026-07-20, debugging the broken-wikilink issue took **~10 minutes** of trial and error because:
- L1 was being run after each fix attempt (4-5 runs)
- The fix was sometimes "rename files" (created .md extension issues) and sometimes "rewrite wikilinks" (had to scan all files for the right pattern)
- Multiple rounds because fixing one issue (e.g., 人物- prefix) sometimes re-introduced another (e.g., orphan because no inbound)

**Future agents**: This file is the single source of truth. Read it before running cleanup_residue.py or doing any wikilink sweep. Each pitfall has a symptom + cause + fix. Apply them preemptively.
