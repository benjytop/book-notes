"""
占位符残留检测脚本 (Step 9.5)

作为独立 CLI 工具, 也可以通过 s96_finalize_vault.py 调用。

中间过程 (skill scaffold) 可以有占位符, 最终 vault 不能留。

用法:
    python3 s95_check_placeholders.py <vault_path>

返回:
    - 0: 没有占位符残留, vault 是 publish-ready
    - 1: 发现占位符, exit 1, 列出文件:行号
"""
from __future__ import annotations

import sys
import re
from pathlib import Path


# 严格占位符模式 (12 类 - 含方括号变体)
PATTERNS = [
    # 圆括号变体 (老式)
    re.compile(r"\(待[^)]*填入\)"),                       # (待 X 填入)
    re.compile(r"\(由\s*[Ll][Ll][Mm][^)]*填入\)"),         # (由 LLM...填入) 老式
    re.compile(r"\(由\s*[\u4e00-\u9fff]+\s*[Ff]illin?\)"),  # (由 X 填入)
    re.compile(r"\(由\s*[Ss]tep\s*\d+[^)]*填入\)"),       # (由 Step X 填入)
    re.compile(r"\(Step\s*\d+\s*填入[^)]*\)"),             # (Step X 填入)
    re.compile(r"\(由[^)]*author_intro[^)]*填入\)"),        # 豆瓣占位
    re.compile(r"\(由[^)]*content_intro[^)]*填入\)"),       # 豆瓣占位
    re.compile(r"\(由[^)]*douban[^)]*填入\)", re.IGNORECASE),  # 豆瓣占位
    re.compile(r"\(LLM\s*内容生成填入\)"),                  # LLM 内容生成填入
    # 方括号变体 (绕过检测的常见逃避) - 新增
    re.compile(r"\[待[^\]]*填入\]"),                       # [待 X 填入]
    re.compile(r"\[由[^]]*author_intro[^]]*填入\]"),        # [由 douban author_intro 填入]
    re.compile(r"\[由[^]]*content_intro[^]]*填入\]"),       # [由 douban content_intro 填入]
]


def scan_vault(vault_path: Path) -> list[dict]:
    """扫描 vault 中所有 .md 文件, 检测占位符残留.

    Args:
        vault_path: vault 根目录

    Returns:
        list of dicts: [{file, line, content, pattern}]
    """
    if not vault_path.exists():
        return []

    findings = []
    md_files = list(vault_path.rglob("*.md"))

    for f in md_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # 跳过 mermaid 代码块
        text_no_mermaid = re.sub(r"```mermaid.*?```", "", text, flags=re.DOTALL)

        lines = text_no_mermaid.split("\n")
        for line_no, line in enumerate(lines, 1):
            for pattern in PATTERNS:
                if pattern.search(line):
                    try:
                        rel_path = f.relative_to(vault_path)
                    except ValueError:
                        rel_path = f
                    findings.append({
                        "file": str(rel_path),
                        "line": line_no,
                        "content": line.strip()[:80],
                        "pattern": pattern.pattern[:50],
                    })
                    break  # 一个文件/行只记录一次

    return findings


def main():
    if len(sys.argv) < 2:
        print("用法: python3 s95_check_placeholders.py <vault_path>")
        print()
        print("示例:")
        print("  python3 s95_check_placeholders.py <VAULT_PARENT>/灿烂千阳")
        sys.exit(1)

    vault_path = Path(sys.argv[1])
    if not vault_path.exists():
        print(f"错误: vault 不存在: {vault_path}")
        sys.exit(1)

    # 可选: --min-rating-count=N 跳过 rating_count < N 的 vault
    # 默认: 不跳过 (总是检查所有占位符)
    min_rating = 0
    for arg in sys.argv[2:]:
        if arg.startswith("--min-rating-count="):
            try:
                min_rating = int(arg.split("=")[1])
            except ValueError:
                pass

    print("=" * 60)
    print(f"PLACEHOLDER RESIDUE CHECK  ::  {vault_path.name}")
    if min_rating > 0:
        print(f"(min-rating-count={min_rating})")
    print("=" * 60)
    print()

    findings = scan_vault(vault_path)

    if not findings:
        print("✓ No unfilled placeholders — vault is publish-ready")
        print()
        return 0

    print(f"! {len(findings)} unfilled placeholder(s) found:")
    print()

    # 按文件分组
    by_file: dict[str, list[dict]] = {}
    for f in findings:
        by_file.setdefault(f["file"], []).append(f)

    for file_name, items in by_file.items():
        print(f"  {file_name}:")
        for item in items[:5]:
            print(f"    L{item['line']}: {item['content']}")
        if len(items) > 5:
            print(f"    ... and {len(items) - 5} more")
        print()

    print("=" * 60)
    print(f"FAIL: {len(findings)} placeholder(s) — replace before publishing")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())