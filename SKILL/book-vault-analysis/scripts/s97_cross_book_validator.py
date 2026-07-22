#!/usr/bin/env python3
"""
s97_cross_book_validator.py - 跨书内容污染检测

通用规则:
  - 检测 vault 中是否包含"非本书类型" 的高频实体/概念 (LLM 错放).
  - 例如 T1 文学的 vault 突然出现 T2 思想史概念, 或 T4 投资的术语.
  - 不需要硬编码具体作者/作品名, 由用户在配置中维护误植黑名单.

默认黑名单 (来自 14-types-taxonomy):
  - T1 文学: 不应高频出现 T2/T4/T5/T6 专属术语
  - T2 思想史: 不应高频出现 T4 投资术语
  - T4 投资: 不应高频出现 T2 思想史之外的术语

配置:
  - 编辑本文件的 TYPE_FORBIDDEN_PATTERNS 字典
  - 或在 vault_root/.book-vault-validator.yaml 自定义

使用方法:
    python3 s97_cross_book_validator.py <vault_path>
"""
import re
import sys
from pathlib import Path

# 类型化误植模式 (通用规则, 不写具体作者元素)
# 格式: {vault_type: [(pattern, description), ...]}
# 这些是"高频但不属于本类型" 的术语. 例如:
#   T1 文学 vault 不应有 T4 投资术语 (橡树资本/钟摆/价值投资)
#   T4 投资 vault 不应有 T2 思想史的 19 位思想家
TYPE_FORBIDDEN_PATTERNS = {
    # T1 文学: 不应包含 T4 投资 / T5 商业 / T6 政经 专属术语
    "T1": [
        (r"橡树资本|喜马拉雅资本|芒格家族|文明3\.0|钟摆",
         "T4 投资术语 (不应出现在 T1 文学)"),
        (r"特朗普|马斯克|共和党|民主党|新右翼|建制派",
         "T6 政经术语 (不应出现在 T1 文学)"),
        (r"纳瓦尔|芒格|巴菲特|自下而上|自由主义",
         "T5 商业术语 (除非是人物背景)"),
    ],
    # T4 投资: 不应包含 T6 政经高频术语 (除非分析政经)
    "T4": [
        (r"特朗普|马斯克|新右翼|建制派|国会事件",
         "T6 政经术语 (T4 投资不应高频出现)"),
    ],
    # T13 旅行: 不应包含 T6 政经 / T2 思想史 专属术语
    "T13": [
        (r"特朗普|共和党|民主党|建制派",
         "T6 政经术语 (不应出现在 T13 旅行)"),
        (r"韦伯|尼采|弗洛伊德|萨特|哈贝马斯",
         "T2 思想史术语 (不应出现在 T13 旅行)"),
    ],
}


def detect_type_mismatch(vault_path: Path, vault_type: str = None) -> dict:
    """
    检测 vault 中是否包含"非本书类型" 的高频术语.

    vault_type: T1/T2/T3/T4/T5/T6/T7/T8/T9/T10/T11/T12/T13/T14
    """
    if vault_type is None:
        # 默认不限制 (没指定类型)
        return {"files_checked": 0, "issues": []}

    rules = TYPE_FORBIDDEN_PATTERNS.get(vault_type, [])
    if not rules:
        return {"files_checked": 0, "issues": []}

    issues = []
    md_files = list(vault_path.rglob("*.md"))

    for f in md_files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for pattern, description in rules:
            matches = re.findall(pattern, content)
            if matches:
                # 找出所在行号
                lines = content.split("\n")
                line_nums = [i + 1 for i, line in enumerate(lines)
                             if re.search(pattern, line)]
                if line_nums:
                    issues.append({
                        "pattern": pattern,
                        "description": description,
                        "file": str(f.relative_to(vault_path)),
                        "lines": line_nums[:5]
                    })

    return {
        "files_checked": len(md_files),
        "issues": issues
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 s97_cross_book_validator.py <vault_path> [vault_type]")
        sys.exit(1)

    vault_path = Path(sys.argv[1])
    vault_type = sys.argv[2] if len(sys.argv) > 2 else None

    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        sys.exit(1)

    print(f"🔍 扫描 vault: {vault_path.name}")
    if vault_type:
        print(f"   类型: {vault_type}")
    print()

    if not vault_type:
        print("⚠️ 未指定类型 (e.g. T1/T2/T4), 跳过类型错配检测")
        print("   用法: python3 s97_cross_book_validator.py <vault_path> T1")
        return 0

    result = detect_type_mismatch(vault_path, vault_type)

    print(f"📊 检查 {result['files_checked']} 个文件")
    print()

    if not result["issues"]:
        print("✅ no type-mismatch pollution detected")
        print("   (0 个误植)")
        return 0

    print(f"⚠️ 类型错配污染: 发现 {len(result['issues'])} 个可疑模式")
    print()

    for issue in result["issues"][:10]:
        line_str = ", ".join(str(l) for l in issue["lines"][:3])
        print(f"  - {issue['file']}:L{line_str}: \"{issue['pattern']}\"")
        print(f"    ({issue['description']})")

    if len(result["issues"]) > 10:
        print(f"  ... +{len(result['issues']) - 10} more")
    print()

    print("💡 提示:")
    print("   - 误植 = LLM 凭训练记忆填了非本书类型的元素")
    print("   - 同作者多本书的引用是合理的 (豁免规则)")
    print("   - 详见 references/llm-inference-pitfall.md")

    return 1


if __name__ == "__main__":
    sys.exit(main())