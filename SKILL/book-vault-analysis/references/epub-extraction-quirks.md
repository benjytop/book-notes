# EPUB extraction quirks (session-specific notes, 2026-07-19)

Quick reference of edge cases hit when extracting OPF data from real-world EPUBs to build vault analyses. Update when new variants appear.

## 1. OPF path variant: `EPUB/package.opf` (not `content.opf`)

Some EPUB sources (notably recent books) store the OPF at `EPUB/package.opf` rather than top-level `content.opf`. Symptom:

```
KeyError: "There is no item named 'content.opf' in the archive"
```

Fix:

```python
def find_opf(z: zipfile.ZipFile) -> str:
    for n in z.namelist():
        if n.endswith(".opf"):
            return n
    raise KeyError("no OPF in archive")
```

Always probe by suffix `*.opf`, never hardcode the path.

## 2. `<item>` attribute order: both `href="..." id="..."` and `id="..." href="..."` are valid

EPUB OPF spec allows `href` and `id` in either order on `<item>`. Calibre-produced EPUBs typically emit `href=` first; some other tools emit `id=` first. Both are valid.

Wrong (single-order only):

```python
items = re.findall(r'<item\s+href="([^"]+)"\s+id="([^"]+)"', opf)
# misses 0 items if OPF has id= before href=
```

Right:

```python
items = re.findall(r'<item\s+href="([^"]+)"\s+id="([^"]+)"', opf)
if not items:
    items = re.findall(r'<item\s+id="([^"]+)"\s+href="([^"]+)"', opf)
    items = [(h, i) for i, h in items]
```

## 3. `[[<book-name>]]` self-reference in MOC is flagged broken

The MOC entry in a vault often uses `[[<book-name>]]` as a link to the book itself, mirroring Douban's "subject" semantic. But the vault's MOC file is `读书脑图.md`, so the validator looks for a file whose stem equals `<book-name>` — finds none — flags broken.

Symptom:

```
[✗] 10. 0 broken wikilinks: FAIL (1 unique: ['<book-name>'])
```

Fix at build time: never reference `<book-name>` from inside the vault; if a section needs to point at the book, use a sibling concept/person note (`[[蔡崇达]]` for the author, `[[皮囊]]` for a previous work, etc.) instead. If `<book-name>` already slipped in via the generator, run:

```python
import re
from pathlib import Path
VAULT = Path("/path/to/vault")
for f in VAULT.rglob("*.md"):
    text = f.read_text(encoding="utf-8", errors="replace")
    new = text.replace("[[<book-name>]]", "[[读书脑图]]")
    if new != text:
        f.write_text(new, encoding="utf-8")
```

The substitution target `[[<book-name>]]` varies per vault; parameterize.

## 4. Quoted-string nesting in vault-build Python — never embed `"X人类"` style strings in `body = "..."`

In Python source for vault builders, mixing inner full-width characters with outer ASCII double-quotes is fine. But inner ASCII `"` inside a string that's already `"..."`-delimited breaks parsing:

```python
# BREAKS
body = "他在说"人类",然后..."

# OK
body = "他在说\"人类\",然后..."
# OR
body = '他在说"人类",然后...'
```

When in doubt and the body has nested punctuation, switch to `write_file` with a separate string literal — `write_file` does not parse Python, so any quote style is fine inside the string. Use this whenever you hit:

```
SyntaxError: invalid syntax. Perhaps you forgot a comma?
```

Caused by inner `"`. Symptom in this session: at least 4 vault builds (费曼学习法, 哲学家们都干了些什么, 我人生最开始的好朋友, and one earlier) all hit this and the only signal was the SyntaxError.

## 5. Douban subject_search — `book.douban.com/subject_search?search_text=...`

This search endpoint returns a JSON blob of matches but **does not return text in the rendered page** for non-browser JS clients. If the curl HTML contains "正在搜索…" placeholder, fall back to `browser_navigate` + `browser_console` extraction:

```js
document.querySelectorAll('a[href*="subject/"]').forEach(a => ({ href: a.href, text: a.textContent.substring(0, 50) }));
```

Or check that the curl output contains the right candidate IDs (`subject/12345`) — if so, you have a usable list even without title text.

## 6. Chinese filename: `《书名》读书脑图` display name vs `读书脑图.md` filename

When MOC uses `《<书名>》读书脑图` as display text, the actual file is `读书脑图.md`. Don't write `<书名>读书脑图.md` as the filename — vault file tree should not have brackets or punctuation in MOC paths.

## 7. Two SKILL spec versions to bump consistently

When patching `book-analysis/SKILL.md` AND `literary-zh-analysis/SKILL.md` together, use the same `version: X.Y.Z` for both. Mismatched versions have happened in this session; future agent calls to `skill_view` may show older version of one and newer of the other.
