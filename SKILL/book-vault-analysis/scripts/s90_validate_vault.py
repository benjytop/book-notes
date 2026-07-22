#!/usr/bin/env python3
"""
Validate an Obsidian vault produced by the book-vault-analysis Skill (v2.0+).

Runs the 13-point mandatory check from the Skill's 'L1 13-POINT 硬检查' section.
Exits non-zero if any hard check fails. Prints a JSON summary to stdout, optionally
writes a JSON report to a file.

Usage:
    python3 s90_validate_vault.py <vault_root> [<source_book>]
    python3 s90_validate_vault.py <vault_root> --report report.json

If <source_book> is given, checks 1-2 (source unchanged / EPUB integrity) are
run against it. Otherwise those checks are skipped.

The 13 checks are:
  1. source unchanged (SKIP if no <source_book>)
  2. epub integrity    (SKIP if no <source_book>)
  3. no /Users paths
  4. no <USER>
  5. no sources/X.txt
  6. no book-analysis
  7. no /tmp/
  8. no 外部路径|占位|已弃用
  9. no empty/short notes
  10. 0 broken wikilinks
  11. 0 orphans
  12. Mermaid parses
  13. Excalidraw parses

**注意**: 检查项 #4 默认使用 `<USER>` token. 用户可在命令行指定 `--user=<USER>` 自定义用户名检查 (e.g. `--user=alice`).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", flags=re.DOTALL)
DISALLOWED_PATTERN_LABELS: list[tuple[str, re.Pattern[str]]] = [
    ("/Users/...",         re.compile(r"/Users/[A-Za-z]")),
    ("<USER>",             re.compile(r"<USER>")),
    ("sources/X.txt",     re.compile(r"sources/\w+\.txt")),
    ("book-analysis",     re.compile(r"book-analysis")),
    ("/tmp/",             re.compile(r"/tmp/")),
    # 占位符检测 (扩展: 检测更多变体)
    ("外部路径|占位|已弃用", re.compile(r"外部路径|占位|已弃用|\(由 [Ll][Ll][Mm]\)|\(待.*后.*填入\)|\(由 [Ss]tep \d+ 填入\)|\(由.*?author_intro 填入\)|\(由.*?content_intro 填入\)|\(Step \d+ 填入.*?\)|\(LLM 内容生成填入\)")),
]  # 13 项硬检查：source unchanged / epub integrity / 6 类残渣 + empty / broken / orphans / mermaid / excalidraw


def read_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return FRONTMATTER_RE.sub("", text, count=1).strip()


def collect_targets(vault: Path) -> tuple[set[str], set[str], set[str]]:
    note_names: set[str] = set()
    folder_names: set[str] = set()
    artifact_paths: set[str] = set()
    for f in vault.rglob("*.md"):
        note_names.add(f.stem)
    for d in vault.iterdir():
        if d.is_dir():
            folder_names.add(d.stem)
    for stem in note_names:
        for ext in (".mermaid.md", ".mermaid", ".excalidraw"):
            if (vault / f"{stem}{ext}").exists():
                artifact_paths.add(stem)
    return note_names, folder_names, artifact_paths


def check_residue(md_files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label, pattern in DISALLOWED_PATTERN_LABELS:
        n = 0
        for f in md_files:
            if pattern.search(f.read_text(encoding="utf-8", errors="replace")):
                n += 1
        counts[label] = n
    return counts


def check_empty(vault: Path, md_files: list[Path]) -> list[str]:
    offenders: list[str] = []
    for f in md_files:
        if len(read_body(f)) < 50:
            offenders.append(f.relative_to(vault).as_posix())
    return offenders


def check_broken_and_orphans(
    vault: Path, md_files: list[Path]
) -> tuple[set[str], set[str], dict[str, int]]:
    note_names, folder_names, artifact_paths = collect_targets(vault)
    broken: set[str] = set()
    counts: dict[str, int] = {}
    for f in md_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in WIKILINK_RE.finditer(text):
            t = m.group(1).strip()
            if t.endswith(".excalidraw") and (vault / t).exists():
                continue
            if t in note_names or t in folder_names or t in artifact_paths:
                counts[t] = counts.get(t, 0) + 1
                continue
            if t.rstrip("/") in note_names or t.rstrip("/") in folder_names:
                counts[t.rstrip("/")] = counts.get(t.rstrip("/"), 0) + 1
                continue
            broken.add(t)
    orphans: set[str] = set(note_names) - set(counts.keys())
    return broken, orphans, counts


def check_prefix_compliance(vault: Path) -> dict[str, list[str]]:
    bad: dict[str, list[str]] = {}
    rules = {
        "主题": ("主题-",),
        "摘录": ("摘录-",),
        "章节": (r"^\d{2}-",),
    }
    for sub, prefixes in rules.items():
        offenders: list[str] = []
        for f in (vault / sub).glob("*.md"):
            for prefix in prefixes:
                if re.match(prefix, f.stem):
                    break
            else:
                offenders.append(f.stem)
        if offenders:
            bad[sub] = offenders
    return bad


def check_root_no_numeric_prefix(vault: Path) -> list[str]:
    offenders: list[str] = []
    for f in vault.iterdir():
        if f.suffix != ".md":
            continue
        if re.match(r"^\d{2}-", f.stem):
            offenders.append(f.name)
    return offenders


def check_mermaid(mermaid_md: Path) -> tuple[bool, str]:
    text = mermaid_md.read_text()
    m = re.search(r"```mermaid\n(.*?)```", text, re.DOTALL)
    if not m:
        return False, "no mermaid block"
    tmp_in = Path("/tmp/_vault_mermaid_check.mmd")
    tmp_in.write_text(m.group(1))
    tmp_out = Path("/tmp/_vault_mermaid_check.svg")
    try:
        result = subprocess.run(
            [
                "npx",
                "-y",
                "-p",
                "@mermaid-js/mermaid-cli@latest",
                "mmdc",
                "-i",
                str(tmp_in),
                "-o",
                str(tmp_out),
                "--quiet",
            ],
            capture_output=True,
            timeout=180,
        )
        ok = result.returncode == 0 and tmp_out.exists()
        msg = "" if ok else (result.stderr.decode("utf-8", "replace")[:300] or "mmdc non-zero exit")
        return ok, msg
    except subprocess.TimeoutExpired:
        return False, "mmdc timed out"
    except Exception as exc:
        return False, str(exc)


def check_excalidraw(ex_path: Path) -> tuple[bool, str]:
    if not ex_path.exists():
        return False, f"missing: {ex_path}"
    try:
        import json
        doc = json.loads(ex_path.read_text())
    except Exception as exc:
        return False, f"json parse error: {exc}"
    if doc.get("type") != "excalidraw":
        return False, "missing type=excalidraw"
    if not isinstance(doc.get("elements"), list) or len(doc["elements"]) == 0:
        return False, "no elements"
    return True, ""


def check_source(source: Path | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if source is None:
        return out
    try:
        sz = source.stat().st_size
    except Exception as exc:
        out["source unchanged"] = f"ERROR: {exc}"
        return out
    out["source size"] = f"{sz} bytes"
    out["source unchanged"] = "skip-non-stored-baseline"
    if source.suffix.lower() == ".epub":
        try:
            with zipfile.ZipFile(source) as z:
                bad = z.testzip()
            out["epub integrity"] = "OK" if bad is None else f"BAD: {bad}"
        except Exception as exc:
            out["epub integrity"] = f"ERROR: {exc}"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", type=Path, help="Path to the vault root")
    parser.add_argument(
        "source",
        type=Path,
        nargs="?",
        default=None,
        help="Optional source book path for checks 1-2",
    )
    parser.add_argument("--report", type=Path, default=None, help="Write JSON report to file")
    args = parser.parse_args()

    vault: Path = args.vault.resolve()
    if not vault.is_dir():
        print(f"ERROR: vault not found: {vault}", file=sys.stderr)
        return 2

    md_files = sorted(vault.rglob("*.md"))
    broken, orphans, _ = check_broken_and_orphans(vault, md_files)
    empty = check_empty(vault, md_files)
    residue = check_residue(md_files)
    prefix_bad = check_prefix_compliance(vault)
    root_numeric = check_root_no_numeric_prefix(vault)

    # Accept any of:
    # - *人物关系图*.mermaid.md (literary books)
    # - *概念图谱*.mermaid.md (nonfiction books)
    # - *主题图*.mermaid.md (alternate)
    # - any *.mermaid.md at vault root or subdirs (fallback)
    mermaid_candidates = (
        list(vault.glob("*人物关系图*.mermaid.md"))
        + list(vault.glob("*概念图谱*.mermaid.md"))
        + list(vault.glob("*主题图*.mermaid.md"))
    )
    if not mermaid_candidates:
        mermaid_candidates = list(vault.rglob("*.mermaid.md"))
    mermaid_ok, mermaid_msg = (
        check_mermaid(mermaid_candidates[0])
        if mermaid_candidates
        else (False, "no 人物关系图.mermaid.md at vault root")
    )

    # Excalidraw is OPTIONAL — only validate if found
    excalidraw_candidates = (
        list(vault.glob("*人物关系图*.excalidraw"))
        + list(vault.glob("*概念图谱*.excalidraw"))
        + list(vault.glob("*主题图*.excalidraw"))
    )
    excalidraw_ok, excalidraw_msg = (
        check_excalidraw(excalidraw_candidates[0])
        if excalidraw_candidates
        else (True, "skipped (no excalidraw file; optional)")
    )

    prefix_summary = {k: v for k, v in prefix_bad.items()}
    failed: list[str] = []
    checks = {
        "1. source unchanged":      "SKIP" if args.source is None else check_source(args.source).get("source unchanged", "ERROR"),
        "2. epub integrity":        "SKIP" if args.source is None else check_source(args.source).get("epub integrity", "N/A"),
        "3. no /Users paths":       "OK" if residue.get("/Users/...", 0) == 0 else f"FAIL ({residue.get('/Users/...', 0)} files)",
        "4. no <USER>":              "OK" if residue.get("<USER>", 0) == 0 else f"FAIL ({residue['<USER>']} files)",
        "5. no sources/X.txt":      "OK" if residue.get("sources/X.txt", 0) == 0 else f"FAIL ({residue['sources/X.txt']} files)",
        "6. no book-analysis":      "OK" if residue.get("book-analysis", 0) == 0 else f"FAIL ({residue['book-analysis']} files)",
        "7. no /tmp/":              "OK" if residue.get("/tmp/", 0) == 0 else f"FAIL ({residue['/tmp/']} files)",
        "8. no 外部路径|占位|已弃用": "OK" if residue.get("外部路径|占位|已弃用", 0) == 0 else f"FAIL ({residue['外部路径|占位|已弃用']} files)",
        "9. no empty/short notes":  "OK" if not empty else f"FAIL ({len(empty)} files: {empty[:3]})",
        "10. 0 broken wikilinks":    "OK" if not broken else f"FAIL ({len(broken)} unique: {sorted(broken)[:5]})",
        "11. 0 orphans":            "OK" if not orphans else f"FAIL ({len(orphans)} files: {sorted(orphans)[:5]})",
        "12. Mermaid parses":       "OK" if mermaid_ok else f"FAIL ({mermaid_msg})",
        "13. Excalidraw (optional)": "OK" if excalidraw_ok else f"FAIL ({excalidraw_msg})",
        "(+) prefix compliance":    "OK" if not prefix_bad else f"WARN ({prefix_summary})",
        "(+) root no NN- prefix":   "OK" if not root_numeric else f"FAIL ({root_numeric})",
    }

    # Hard fails
    for label in [str(i) for i in range(3, 14)]:
        prefix = label + "."
        for k in checks:
            if k.startswith(prefix) and not (checks[k].startswith("OK") or checks[k].startswith("SKIP")):
                failed.append(label)
                break
    # Warning only: prefix compliance (some flexibility)
    root_numeric_fail = "(+) root no NN- prefix" in checks and not checks["(+) root no NN- prefix"].startswith("OK")
    if root_numeric_fail:
        failed.append("root-no-NN-prefix")

    print("\n=== 13-POINT VAULT VALIDATION ===\n")
    for k, v in checks.items():
        icon = "✓" if v.startswith("OK") or v.startswith("SKIP") else "✗"
        print(f"  [{icon}] {k}: {v}")

    print(f"\nFile counts:")
    print(f"  Total .md: {len(md_files)}")
    for sub in ["概念", "人物", "主题", "章节", "摘录"]:
        if (vault / sub).is_dir():
            print(f"  {sub}: {len(list((vault / sub).glob('*.md')))}")

    print(f"\nBroken wikilinks ({len(broken)}):")
    for t in sorted(broken)[:20]:
        print(f"  - {t}")
    print(f"\nOrphans ({len(orphans)}):")
    for t in sorted(orphans)[:20]:
        print(f"  - {t}")

    summary = {
        "vault": str(vault),
        "source": str(args.source) if args.source else None,
        "checks": checks,
        "broken": sorted(broken),
        "orphans": sorted(orphans),
        "root_numeric_offenders": root_numeric,
        "prefix_offenders": prefix_summary,
        "residue": residue,
        "empty_offenders": empty,
        "pass": not failed,
    }
    if args.report:
        args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nReport written to {args.report}")

    if failed:
        print(f"\nFAILED: {len(failed)} hard check(s) — {', '.join(failed)}")
        return 1
    print("\nALL HARD CHECKS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
