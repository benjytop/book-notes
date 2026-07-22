"""
Finalize-Vault validator — runs AFTER the 13-point hard check.

Checks:
- File-level anomalies (zero-byte, odd chars in filename, junk dirs like README.md<)
- Structure-level (zero-inbound orphans frontmatter)
- Network-level (broken subgraph: notes that can't reach MOC through any wikilink)
- Frontmatter hygiene (type field, title consistency)
- Residue scan over the full file tree

Usage:
    python3 s96_finalize_vault.py <vault_path> [--report report.json]

Exits non-zero ONLY if a HARD issue is found.
Warnings are listed but do not fail the script.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", flags=re.DOTALL)


def read_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if FRONTMATTER_RE.match(text):
        text = FRONTMATTER_RE.sub("", text, count=1).strip()
    return text


def collect_targets(vault: Path) -> tuple[set[str], set[str], set[str]]:
    note_names = {f.stem for f in vault.rglob("*.md")}
    folder_names = {f.stem for f in vault.iterdir() if f.is_dir()}
    artifact_paths = set()
    for stem in note_names:
        for ext in (".mermaid.md", ".excalidraw", ".mermaid"):
            if (vault / f"{stem}{ext}").exists():
                artifact_paths.add(stem)
    return note_names, folder_names, artifact_paths


def check_file_anomalies(vault: Path) -> dict[str, list[str]]:
    """Find files / directories with suspicious names or sizes."""
    issues: dict[str, list[str]] = {
        "zero_byte": [],
        "suspicious_name": [],
        "junk_dirs": [],
        "odd_extensions": [],
    }

    for f in vault.rglob("*"):
        rel = f.relative_to(vault)
        # Zero-byte files (excluding empty .md)  - we only care about non-empty
        if f.is_file() and f.suffix == ".md" and f.stat().st_size < 30:
            issues["zero_byte"].append(str(rel))

        # Suspicious characters in filename
        if re.search(r"[<>|&$\\;?*\"'`]", f.name):
            issues["suspicious_name"].append(str(rel))

        # Junk dirs: created by tool errors (e.g. README.md<, README.md</path>)
        if f.is_dir() and ("<" in f.name or ">" in f.name):
            issues["junk_dirs"].append(str(rel))

        # Non-.md files at vault root — not strictly wrong, but suspect
        if f.is_file() and not f.suffix in (".md", ".mermaid.md", ".excalidraw", ".png", ".svg"):
            if not any(part.startswith(".") for part in f.parts):  # skip hidden
                issues["odd_extensions"].append(str(rel))

    return {k: v for k, v in issues.items() if v}


def check_frontmatter_hygiene(md_files: list[Path]) -> dict[str, list[str]]:
    """Validate that notes have frontmatter (title, type, etc.).

    Skip .mermaid.md files (they're diagrams, not notes) and graph files.
    For titles, we reject only a narrow set of characters that would break
    wikilink parsing or YAML structure. CJK brackets / quotes are fine.
    """
    missing_title = []
    missing_type = []
    sub_50char = []
    bad_titles = []

    # A title is "bad" only if it contains characters that break YAML or wikilinks
    # We exclude:   " ' #
    # We DO allow:   < > | & 中文标点 《》 "" ''
    bad_chars_re = re.compile(r"""["'#]""")

    def extract_title_value(raw):
        """Strip surrounding YAML quotes from a title field value."""
        s = raw.strip()
        if s.startswith('"') and s.endswith('"') and len(s) >= 2:
            return s[1:-1]
        if s.startswith("'") and s.endswith("'") and len(s) >= 2:
            return s[1:-1]
        return s

    for f in md_files:
        # Skip diagram / graph files that don't need frontmatter
        if f.suffix == ".md" and (f.name.endswith("图谱.mermaid.md") or f.name == "人物关系图.mermaid.md" or f.name == "概念图谱.mermaid.md"):
            continue

        text = f.read_text(encoding="utf-8", errors="replace")
        m = FRONTMATTER_RE.match(text)
        if not m:
            missing_title.append(f.name)
            continue
        fm = m.group(1)
        title_match = re.search(r"title:\s*(.*)", fm)
        type_match = re.search(r"type:\s*(\S+)", fm)
        if not title_match:
            missing_title.append(f.name)
        else:
            title_value = extract_title_value(title_match.group(1))
            if bad_chars_re.search(title_value):
                bad_titles.append(f.name + f" : {title_value}")
        if not type_match:
            missing_type.append(f.name)

        body = read_body(f)
        if len(body.strip()) < 50 and len(text.strip()) > 200:
            sub_50char.append(f.name)

    return {
        "missing_title": missing_title,
        "bad_titles": bad_titles,
        "missing_type": missing_type,
        "sub_50char_body": sub_50char,
    }


def check_network_reachability(vault: Path) -> dict[str, list[str]]:
    """Find notes that cannot reach MOC through any wikilink chain.

    A note is "reachable" if there's a path of wikilinks from itself to MOC,
    OR it has an inbound wikilink from a reachable note (transitive reach).
    """
    md_files = list(vault.rglob("*.md"))
    note_names = {f.stem for f in md_files}
    folder_names = {f.stem for f in vault.iterdir() if f.is_dir()}
    all_names = note_names | folder_names

    # Build adjacency: per-note set of outbound wikilinks.
    # Only track targets that exist as note files (skip folder-only refs).
    outbound: dict[str, set[str]] = {n: set() for n in note_names}
    inbound: dict[str, set[str]] = {n: set() for n in note_names}
    for f in md_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in WIKILINK_RE.finditer(text):
            t = m.group(1).strip()
            target = t.rstrip("/") if t.endswith("/") else t
            if target in note_names:
                outbound[f.stem].add(target)
                inbound[target].add(f.stem)

    # MOC stem names to try
    moc_candidates = [n for n in note_names if "读书脑图" in n or "moc" in n.lower()]
    if not moc_candidates:
        return {"unreachable_from_moc": [], "isolated": [], "missing_moc": True}

    # BFS from any MOC
    reachable = set(moc_candidates)
    frontier = list(moc_candidates)
    while frontier:
        next_frontier = []
        for node in frontier:
            for child in outbound.get(node, set()):
                if child not in reachable:
                    reachable.add(child)
                    next_frontier.append(child)
        frontier = next_frontier

    unreachable = sorted(set(note_names) - reachable)
    # Isolated: notes with NO inbound AND NO outbound wikilinks
    isolated = sorted([
        n for n in note_names
        if not inbound.get(n) and not outbound.get(n)
    ])

    return {
        "unreachable_from_moc": unreachable,
        "isolated": isolated,
        "missing_moc": False,
    }


def check_residue_extra(md_files: list[Path]) -> dict[str, int]:
    """Extra residue patterns beyond validate_vault.py's 13 checks.

    Note: `NN-第N部-...md` files inside `章节/` are LEGITIMATE per the Skill's
    chapter-folder prefix convention. We only flag `NN-` prefix leakage at root.
    """
    bad_patterns = {
        "MOC-":        re.compile(r"MOC-读书脑图"),
        "NN-root-prefix":  re.compile(r"^NN[-第]"),  # NN- prefix at root or root-level
        "skill-ref":   re.compile(r"book-vault-analysis|skill\s*[a-z_-]+"),
        "todo-flag":   re.compile(r"\bTODO\b|\bFIXME\b|\bXXX\b"),
    }
    counts: dict[str, list[str]] = {}
    for label, pattern in bad_patterns.items():
        hits = []
        for f in md_files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                if pattern.search(text) or (label == "NN-root-prefix" and pattern.search(f.name)):
                    hits.append(str(f.relative_to(f.parents[len(f.parts)-3])))
            except Exception:
                continue
        if hits:
            counts[label] = hits[:5]
    return counts


def check_unfilled_placeholders(md_files: list[Path]) -> dict[str, list[dict]]:
    """检测 vault 中是否有未替换的占位符 (process-only, NOT final-vault).

    占位符模式 (来自 skill scaffold 模板):
    - "(待 X 填入)" / "(待 X 抽[取/填入])" - skill 模板
    - "(由 [Ll][Ll][Mm] ... 填入)" - 老式占位符
    - "(由 .* 抽[取] .* 填入)"
    - "(Step [0-9]+ 填入)" - 老式
    - "(由 Step .* 填入)"
    - "(由 .* author_intro 填入)"
    - "(由 .* content_intro 填入)"
    - "(LLM 内容生成填入)"
    - "(LLM 抽取后填入)"
    - "(Step 8 填入完整内容)"

    每发现一处, 记录文件:行号:原文.

    中间过程可以保留 (skill 模板), 但最终 vault 不能留.
    """
    # 严格占位符模式 (作为硬 issue 处理)
    PATTERNS = [
        re.compile(r"\(待[^)]*填入\)"),                       # (待 X 填入)
        re.compile(r"\(由\s*[Ll][Ll][Mm][^)]*填入\)"),         # (由 LLM...填入) 老式
        re.compile(r"\(由\s*[\u4e00-\u9fff]+\s*[Ff]illin?\)"),  # (由 X 填入)
        re.compile(r"\(由\s*[Ss]tep\s*\d+[^)]*填入\)"),       # (由 Step X 填入)
        re.compile(r"\(Step\s*\d+\s*填入[^)]*\)"),             # (Step X 填入)
        re.compile(r"\(由[^)]*author_intro[^)]*填入\)"),        # 豆瓣占位
        re.compile(r"\(由[^)]*content_intro[^)]*填入\)"),       # 豆瓣占位
        re.compile(r"\(由[^)]*douban[^)]*填入\)", re.IGNORECASE),  # 豆瓣占位
        re.compile(r"\(LLM\s*内容生成填入\)"),                  # LLM 内容生成填入
    ]

    findings: list[dict] = []
    for f in md_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = text.split("\n")
        for line_no, line in enumerate(lines, 1):
            for pattern in PATTERNS:
                if pattern.search(line):
                    findings.append({
                        "file": str(f.relative_to(f.parents[len(f.parts)-3])),
                        "line": line_no,
                        "content": line.strip()[:80],
                        "pattern": pattern.pattern[:50],
                    })
                    break  # 一个文件/行只记录一次

    # 按文件分组
    by_file: dict[str, list[dict]] = {}
    for f in findings:
        f_name = f["file"]
        if f_name not in by_file:
            by_file[f_name] = []
        by_file[f_name].append(f)

    return {"unfilled_placeholders": findings, "by_file": by_file, "count": len(findings)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vault", type=Path, help="Path to the vault root")
    parser.add_argument("--report", type=Path, default=None, help="Write JSON report to file")
    args = parser.parse_args()

    vault: Path = args.vault.resolve()
    if not vault.is_dir():
        print(f"ERROR: vault not found: {vault}", file=sys.stderr)
        return 2

    md_files = list(vault.rglob("*.md"))

    print("="*60)
    print(f"FINALIZE-VAULT VALIDATION  ::  {vault.name}")
    print("="*60 + "\n")

    # 1. File-level
    file_anom = check_file_anomalies(vault)
    print("[1] File-level anomalies")
    if not file_anom:
        print("    ✓ No file anomalies found")
    else:
        for k, lst in file_anom.items():
            print(f"    ! {k}: {len(lst)} item(s)")
            for p in lst[:5]:
                print(f"      - {p}")
    print()

    # 2. Frontmatter
    fm = check_frontmatter_hygiene(md_files)
    print("[2] Frontmatter hygiene")
    if not fm["missing_title"] and not fm["missing_type"] and not fm["bad_titles"] and not fm["sub_50char_body"]:
        print("    ✓ All notes have valid frontmatter (title + type)")
    else:
        if fm["missing_title"]:
            print(f"    ! missing title: {len(fm['missing_title'])} note(s)")
            for p in fm["missing_title"][:5]:
                print(f"      - {p}")
        if fm["missing_type"]:
            print(f"    ! missing type: {len(fm['missing_type'])} note(s)")
            for p in fm["missing_type"][:5]:
                print(f"      - {p}")
        if fm["bad_titles"]:
            for t in fm["bad_titles"][:5]:
                print(f"    ! bad title: {t}")
        if fm["sub_50char_body"]:
            print(f"    ! sub-50 char body: {len(fm['sub_50char_body'])} note(s)")
    print()

    # 3. Network reachability
    net = check_network_reachability(vault)
    print("[3] Wikilink network reachability")
    if net.get("missing_moc"):
        print("    ! NO 读书脑图.md / MOC file found at vault root")
    else:
        if net["unreachable_from_moc"]:
            print(f"    ! {len(net['unreachable_from_moc'])} note(s) unreachable from MOC:")
            for n in net["unreachable_from_moc"][:10]:
                print(f"      - {n}")
        else:
            print("    ✓ All notes reachable from 读书脑图 (BFS)")
        if net["isolated"]:
            print(f"    ! {len(net['isolated'])} isolated note(s) (no in/out links):")
            for n in net["isolated"][:5]:
                print(f"      - {n}")
        else:
            print("    ✓ No notes are totally isolated")
    print()

    # 4. Residue extra
    residue = check_residue_extra(md_files)
    print("[4] Extra residue scan")
    if not residue:
        print("    ✓ No extra residue detected")
    else:
        for k, lst in residue.items():
            print(f"    ! {k}: {len(lst)} hit(s)")
            for p in lst[:3]:
                print(f"      - {p}")
    print()

    # 5. Unfilled placeholders (硬 issue: 最终 vault 不能留占位符)
    placeholders = check_unfilled_placeholders(md_files)
    print("[5] Unfilled placeholder residue (HARD)")
    if placeholders["count"] == 0:
        print("    ✓ No unfilled placeholders — vault is publish-ready")
    else:
        print(f"    ! {placeholders['count']} unfilled placeholder(s):")
        for f_name, items in placeholders["by_file"].items():
            print(f"      {f_name}:")
            for item in items[:3]:
                print(f"        L{item['line']}: {item['content']}")
            if len(items) > 3:
                print(f"        ... and {len(items)-3} more")
    print()

    # Build summary
    hard_issues = (
        len(file_anom.get("junk_dirs", []))
        + len(file_anom.get("zero_byte", []))
        + len(file_anom.get("suspicious_name", []))
        + len(net.get("unreachable_from_moc", []))
        + len(net.get("isolated", []))
        + len(fm.get("missing_title", []))
        + placeholders["count"]  # 占位符未替换 = 硬 issue
    )
    soft_issues = (
        sum(len(v) for v in file_anom.values())
        + len(fm.get("bad_titles", []))
        + len(fm.get("sub_50char_body", []))
        + sum(len(v) for v in residue.values())
    )

    print("="*60)
    print(f"SUMMARY  ::  hard = {hard_issues}  soft = {soft_issues}")
    print("="*60)

    summary = {
        "vault": str(vault),
        "total_md": len(md_files),
        "file_anomalies": file_anom,
        "frontmatter_issues": fm,
        "network": net,
        "extra_residue": residue,
        "placeholders": placeholders,
        "hard_issues": hard_issues,
        "soft_issues": soft_issues,
        "pass": hard_issues == 0,
    }
    if args.report:
        args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if hard_issues:
        print(f"\nFAIL: {hard_issues} hard issue(s) — fix before publishing")
        return 1
    print(f"\nPASS: Vault is publish-ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
