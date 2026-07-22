"""
构建完整 Obsidian vault。

阶段:
  --phase=scaffold   Step 5: 创建 9 个根目录文件 + 4 个通用子目录
  --phase=entities   Step 6: 填充类型化子目录 + 章节
  --phase=mermaid    Step 7: 生成 Mermaid
  --phase=moc        Step 8: 更新 MOC + 涉及人物 + 阅读方式
  (无参数)           按顺序运行所有阶段

参数:
  <VAULT>            vault 路径
  --type=T{N}         14 大类之一 (T1-T14), 默认 T1
  --scratch=<DIR>    spine 抽取目录, 默认当前目录/scratch/
  --phase=<phase>    scaffold | entities | mermaid | moc

用法:
    python3 s50_build_vault.py <VAULT> --phase=scaffold --type=T1
    python3 s50_build_vault.py <VAULT> --phase=entities --type=T1 --scratch=./scratch

注: 本 skill 的脚本在 Mac + Python 3 下开发验证。
    移植到其他平台可能需要小调整 (例如解释器名称, 路径分隔符)。

本脚本是 book-vault-analysis 的核心:
- 自动生成 wikilink (避免人肉笔误)
- 应用 C1-C12 易读性约束
- 创建类型化目录结构
- 嵌入所有元数据
"""
import sys
import json
import re
import shutil
from pathlib import Path
from datetime import date

# ========================
# 类型特定配置
# ========================

# 14 大类的 vault 子目录 + Mermaid 文件名
TYPE_VAULT = {
    "T1":  {"subdirs": ["人物", "事件", "地点"], "mermaid": "人物关系图.mermaid.md"},
    "T2":  {"subdirs": ["思想家", "概念", "思想流派"], "mermaid": "思想影响图.mermaid.md"},
    "T3":  {"subdirs": ["概念", "方法", "步骤"], "mermaid": "概念图谱.mermaid.md"},
    "T4":  {"subdirs": ["思想家", "理论", "模型", "案例"], "mermaid": "理论关系图.mermaid.md"},
    "T5":  {"subdirs": ["原则", "案例", "框架"], "mermaid": "框架图.mermaid.md"},
    "T6":  {"subdirs": ["人物", "事件", "阵营", "概念"], "mermaid": "阵营-人物图.mermaid.md"},
    "T7":  {"subdirs": ["人物", "事件", "地点", "概念"], "mermaid": "时间线-人物图.mermaid.md"},
    "T8":  {"subdirs": ["概念", "理论", "方法", "案例"], "mermaid": "概念图谱.mermaid.md"},
    "T9":  {"subdirs": ["概念", "理论", "案例", "原理"], "mermaid": "概念关系图.mermaid.md"},
    "T10": {"subdirs": ["概念", "理论", "方法", "案例"], "mermaid": "概念图谱.mermaid.md"},
    "T11": {"subdirs": ["人物", "作品", "风格", "概念"], "mermaid": "人物-风格图.mermaid.md"},
    "T12": {"subdirs": ["概念", "方法", "案例"], "mermaid": "概念图谱.mermaid.md"},
    "T13": {"subdirs": ["地点", "人物", "事件", "概念"], "mermaid": "人物-地点图.mermaid.md"},
    "T14": {"subdirs": [], "mermaid": "类型化"},
}

# 通用子目录 (所有类型都有)
UNIVERSAL_SUBDIRS = ["概念", "主题", "摘录", "章节"]

# 根目录文件
ROOT_FILES = ["00-封面.md", "01-导言-评论.md", "读书脑图.md", "无剧透导读.md",
              "全书结构.md", "章节地图.md", "主题与核心观点.md", "阅读问题.md",
              "复习卡片.md", "README.md"]

TODAY = date.today().isoformat()  # 2026-07-20


# ========================
# 工具函数
# ========================

def write_file(path: Path, content: str):
    """写入文件, 自动创建父目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def format_word_count(total_chars: int) -> str:
    """C12 字数规则: ≥ 10,000 → "XX.X 万字", < 10,000 → 整数."""
    if total_chars >= 10000:
        return f"{total_chars / 10000:.1f} 万字"
    else:
        return f"{total_chars} 字"


def cn_num(n: int) -> str:
    """转换整数为中文章节数字。"""
    nums = {
        1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十",
        11: "十一", 12: "十二", 13: "十三", 14: "十四", 15: "十五",
        16: "十六", 17: "十七", 18: "十八", 19: "十九", 20: "二十",
        21: "二十一", 22: "二十二", 23: "二十三", 24: "二十四", 25: "二十五",
        26: "二十六", 27: "二十七", 28: "二十八", 29: "二十九", 30: "三十",
    }
    return nums.get(n, str(n))


# ========================
# 阶段: scaffold
# ========================

def phase_scaffold(vaull: Path, type_code: str, sub_name: str, meta: dict):
    """创建 9 个根目录文件 + 4 个通用子目录。"""
    vaull.mkdir(parents=True, exist_ok=True)
    for sub in UNIVERSAL_SUBDIRS:
        (vaull / sub).mkdir(exist_ok=True)

    # 0. 封面
    write_file(vaull / "00-封面.md", f"""---
title: 封面
book: "{meta['title']}"
type: cover
created: {TODAY}
updated: {TODAY}
tags: [cover]
---

# 《{meta['title']}》封面

## 书目信息

- 书名: {meta['title']}
- 作者: {meta['creator'] or '未知'}
- 出版社: {meta['publisher'] or '未知'}

## 设计意图

封面由出版方设计, 此处作为 vault 入口标识。
""")

    # 1. 导言 - 评论
    write_file(vaull / "01-导言-评论.md", f"""---
title: 导言 - 评论
book: "{meta['title']}"
type: introduction
created: {TODAY}
updated: {TODAY}
tags: [introduction]
---

# 导言 - 出版商评论

## 出版方简介

> 待豆瓣数据嵌入后填入

## 内容简介

> 待豆瓣数据嵌入后填入

## 评 论

> 待豆瓣数据嵌入后填入
""")

    # 2. 无剧透导读
    write_file(vaull / "无剧透导读.md", f"""---
title: 无剧透导读
book: "{meta['title']}"
type: reading-guide
created: {TODAY}
updated: {TODAY}
tags: [guide]
---

# 《{meta['title']}》无剧透导读

## 这本书在处理什么问题/冲突

(待实体抽取后填入)

## 结构总览

(待章节地图填入)

## 适合谁读

(待 LLM 抽取后填入)
""")

    # 3. 全书结构
    write_file(vaull / "全书结构.md", f"""---
title: 全书结构
book: "{meta['title']}"
type: structure
created: {TODAY}
updated: {TODAY}
tags: [structure]
---

# 全书结构

(待章节抽取后填入时间线 + 部结构)
""")

    # 4. 章节地图
    write_file(vaull / "章节地图.md", f"""---
title: 章节地图
book: "{meta['title']}"
type: chapter-map
created: {TODAY}
updated: {TODAY}
tags: [chapter-map]
---

# 章节地图

(待章节抽取后填入所有章节 wikilink 列表)
""")

    # 5. 主题与核心观点
    write_file(vaull / "主题与核心观点.md", f"""---
title: 主题与核心观点
book: "{meta['title']}"
type: themes
created: {TODAY}
updated: {TODAY}
tags: [themes]
---

# 主题与核心观点

## 核心命题

(待 LLM 抽取后填入)

## 主题笔记

(待 entities phase 填入 5 个主题 wikilink)
""")

    # 6. 阅读问题
    write_file(vaull / "阅读问题.md", f"""---
title: 阅读问题
book: "{meta['title']}"
type: questions
created: {TODAY}
updated: {TODAY}
tags: [questions]
---

# 阅读问题

(待 LLM 抽取后填入 10 个阅读问题)
""")

    # 7. 复习卡片
    write_file(vaull / "复习卡片.md", f"""---
title: 复习卡片
book: "{meta['title']}"
type: review-cards
created: {TODAY}
updated: {TODAY}
tags: [review]
---

# 复习卡片

(待 LLM 抽取后填入 Q&A 卡片)
""")

    # 8. README
    write_file(vaull / "README.md", f"""---
title: "《{meta['title']}》Obsidian Vault"
created: {TODAY}
updated: {TODAY}
type: readme
tags: [readme, vault]
---

# 《{meta['title']}》Obsidian Vault

{meta['creator'] or '未知'}《{meta['title']}》结构化分析 vault。入口在 [[读书脑图]]。

## 目录结构

- [[读书脑图]] - MOC 索引
- [[封面]] / [[导言-评论]]
- [[无剧透导读]] / [[全书结构]] / [[章节地图]]
- [[主题与核心观点]] / [[复习卡片]] / [[阅读问题]]
- 概念/主题/摘录/章节 - 各子目录

## 验证状态

- L1: 13-POINT 硬检查
- L2: 4 类软检查
- 目标: hard=0, soft=0
""")

    # 9. MOC (Step 8 填入完整内容)
    write_file(vaull / "读书脑图.md", f"""---
title: 读书脑图
book: "{meta['title']}"
type: moc
created: {TODAY}
updated: {TODAY}
tags: [moc, {type_code}, {sub_name}]
---

# 《{meta['title']}》读书脑图

> 入口与索引页。从这里可以跳转到每一篇笔记。

## 书籍信息

1. 作者：{meta.get('creator', '未知')}
2. 译者：(待填入)
3. 出版社：{meta.get('publisher', '未知')}
4. 出版年：(待填入)
5. ISBN：(待填入)
6. 页数：(待填入)
7. 原作名：(待填入)
8. **类型：{type_code} {sub_name}**
9. **字数：{format_word_count(meta['total_chars'])}**
10. 豆瓣评分：(待豆瓣数据嵌入后填入)

## 豆瓣数据

(待豆瓣数据嵌入后填入)

## 阅读方式 (7 种阅读法中必选 4-5 种)

(待 LLM 抽取后填入)

## 章节结构

(由 entities phase 自动填入)

## 涉及人物

(由 entities phase 自动填入)

## 核心概念

(由 entities phase 自动填入)

## 主题

(由 entities phase 自动填入)

## 关键摘录

(由 entities phase 自动填入)

## 阅读路径

### 阅读前
(由 LLM 抽取后填入)

### 阅读中
(由 LLM 抽取后填入)

### 阅读后
(由 LLM 抽取后填入)

## 关系图

(待 mermaid phase 自动填入)

## 附录

(由 LLM 抽取后填入)
""")

    print(f"✓ Phase scaffold 完成: 9 个根目录文件 + 4 个子目录")


# ========================
# 阶段: entities (创建子目录结构, 准备实体填充)
# ========================

def phase_entities(vaull: Path, type_code: str, people_data: list = None,
                   concepts_data: list = None, themes_data: list = None,
                   quotes_data: list = None, chapters_data: list = None):
    """
    创建类型化子目录结构 + 填充 LLM 抽取的内容 (Step 6)。

    子目录创建规则 (按 type_code):
    - T1 文学: 人物/事件/地点
    - T2 思想史: 思想家/概念/思想流派
    - ... (见 TYPE_VAULT)

    内容填充:
    - people_data: list of dicts, 每个 {name, content (markdown)}
    - concepts_data: list of dicts, 每个 {name, content}
    - themes_data: list of dicts, 每个 {name, content} (前缀 主题-)
    - quotes_data: list of dicts, 每个 {name, content} (前缀 摘录-NN-)
    - chapters_data: list of dicts, 每个 {name, content} (部目录按 N-部名, 文件按 NN-章名)
    """
    import json

    type_info = TYPE_VAULT.get(type_code, {})
    subdirs = type_info.get("subdirs", [])

    # 1. 创建子目录
    for sub in subdirs:
        (vaull / sub).mkdir(parents=True, exist_ok=True)
    for sub in UNIVERSAL_SUBDIRS:
        (vaull / sub).mkdir(parents=True, exist_ok=True)

    # 章节/ 的部目录 (T1 文学专用)
    if type_code == "T1":
        for part in ["1-第一部", "2-第二部", "3-第三部", "4-第四部"]:
            (vaull / "章节" / part).mkdir(parents=True, exist_ok=True)

    # 2. 填充人物档案 (按 vault 子目录, 如 人物/)
    if people_data:
        # 按 type_info 推断人物目录
        people_dir_name = subdirs[0] if subdirs else "人物"
        # 特殊: T2 思想史用 "思想家", T11 艺术用 "人物"
        if type_code in ("T2", "T11"):
            people_dir_name = subdirs[0]
        elif type_code in ("T4",):
            people_dir_name = "思想家"

        target_dir = vaull / people_dir_name
        target_dir.mkdir(parents=True, exist_ok=True)

        for person in people_data:
            name = person["name"]
            content = person["content"]
            write_file(target_dir / f"{name}.md", content)
        print(f"  ✓ {len(people_data)} 人物档案写入 {people_dir_name}/")

    # 3. 填充概念 (通用目录 概念/)
    if concepts_data:
        target_dir = vaull / "概念"
        target_dir.mkdir(parents=True, exist_ok=True)
        for concept in concepts_data:
            name = concept["name"]
            content = concept["content"]
            write_file(target_dir / f"{name}.md", content)
        print(f"  ✓ {len(concepts_data)} 概念笔记写入 概念/")

    # 4. 填充主题 (主题/ + 前缀 主题-)
    if themes_data:
        target_dir = vaull / "主题"
        target_dir.mkdir(parents=True, exist_ok=True)
        for theme in themes_data:
            name = theme["name"]
            content = theme["content"]
            write_file(target_dir / f"主题-{name}.md", content)
        print(f"  ✓ {len(themes_data)} 主题笔记写入 主题/")

    # 5. 填充摘录 (摘录/ + 前缀 摘录-NN-)
    if quotes_data:
        target_dir = vaull / "摘录"
        target_dir.mkdir(parents=True, exist_ok=True)
        for quote in quotes_data:
            name = quote["name"]
            content = quote["content"]
            write_file(target_dir / f"摘录-{name}.md", content)
        print(f"  ✓ {len(quotes_data)} 摘录写入 摘录/")

    # 6. 填充章节 (章节/部目录/NN-章名.md)
    if chapters_data:
        for chapter in chapters_data:
            name = chapter["name"]      # e.g., "01-第一章" 或 "00-前言-第一部"
            content = chapter["content"]
            part = chapter.get("part")  # e.g., "1-第一部"
            if part:
                write_file(vaull / "章节" / part / f"{name}.md", content)
            else:
                write_file(vaull / "章节" / f"{name}.md", content)
        print(f"  ✓ {len(chapters_data)} 章节笔记写入 章节/")

    total = (len(people_data or []) + len(concepts_data or []) +
             len(themes_data or []) + len(quotes_data or []) +
             len(chapters_data or []))
    print(f"✓ Phase entities 完成: 类型化子目录 + {total} 个内容文件 ({type_code})")


# ========================
# 阶段: fix-wikilinks (修复常见的 wikilink 问题)
# ========================

def phase_fix_wikilinks(vaull: Path):
    """
    自动修复常见的 wikilink 问题, 避免人工修复循环。

    修复规则:
    1. 路径式 wikilink: `[[1-第一章/00-前言-XXX]]` → `**目录/**` (加粗文字)
    2. 前缀错位: `[[人物-玛丽雅姆]]` → `[[玛丽雅姆]]` (人物/在目录名前缀)
    3. MOC 名称不一致: 自动同步
    """
    fixed_count = 0

    # 1. 路径式 wikilink → 加粗文字
    for f in vaull.rglob("*.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        orig = text
        # 检测 `[[目录/文件]]` 模式 (Obsidian wikilink 不支持路径)
        text = re.sub(r'\[\[([\d]+-[^/]+/[\d]+-[^\]]+)\]\]', r'**\1/**', text)
        text = re.sub(r'\[\[([\d]+-[^/]+/00-前言-[^\]]+)\]\]', r'**\1/**', text)
        if text != orig:
            f.write_text(text, encoding="utf-8")
            fixed_count += 1

    # 2. wikilink 前缀错位
    for f in vaull.rglob("*.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        orig = text
        for prefix in ["事件-", "地点-", "思想流派-", "方法-", "步骤-",
                       "理论-", "模型-", "案例-", "原则-", "框架-",
                       "阵营-", "作品-", "风格-"]:
            # 注意: "人物-", "概念-", "主题-" 是合法前缀 (因为文件名带这些前缀), 不应剥离
            text = re.sub(r'\[\[' + re.escape(prefix) + r'([^\]]+)\]\]',
                         r'[[\1]]', text)
        if text != orig:
            f.write_text(text, encoding="utf-8")
            fixed_count += 1

    # 3. 检查文件名前言统一 (兜底)
    #    任何 `00-前言-XXX` 文件 (无 .md 后缀), 强制加 .md
    for f in list(vaull.rglob("*")):
        if f.is_file() and f.suffix == "" and f.name.startswith("00-前言"):
            new_name = f.with_suffix(".md")
            if not new_name.exists():
                f.rename(new_name)
                fixed_count += 1

    print(f"✓ Phase fix-wikilinks 完成: 修复 {fixed_count} 处")
    return fixed_count


# ========================
# 阶段: mermaid (占位 - 实际由 LLM 生成)
# ========================

def phase_mermaid(vaull: Path, type_code: str, mermaid_content: str = None):
    """
    生成 Mermaid 关系图 (Step 7)。

    Args:
        mermaid_content: 完整的 mermaid markdown 内容 (含 ```mermaid 块)
                         如果为 None, 创建占位文件
    """
    type_info = TYPE_VAULT.get(type_code, {})
    mermaid_filename = type_info.get("mermaid", "类型化.mermaid.md")

    if mermaid_content is None:
        mermaid_content = """```mermaid
%% 占位 Mermaid 文件, 由 LLM 内容生成覆盖
graph TD
    placeholder[Placeholder]
```"""

    write_file(vaull / mermaid_filename, mermaid_content)
    print(f"✓ Phase mermaid: {mermaid_filename} ({len(mermaid_content)} 字符)")


# ========================
# 阶段: moc (创建/更新 MOC, 含跨链修复)
# ========================

def phase_moc(vaull: Path, type_code: str, sub_name: str, meta: dict):
    """
    更新 MOC, 含自动跨链修复。

    关键修复:
    - 自动建立 MOC → 所有 .md 文件的入链 (避免 orphan)
    - MOC 的 wikilink 优先 bare-stem (无路径前缀)
    """

    # 1. 收集 vault 内所有 .md 文件的 stem
    all_stems = set()
    for f in vaull.rglob("*.md"):
        all_stems.add(f.stem)

    # 2. 先运行 fix-wikilinks (避免 orphan 出现)
    phase_fix_wikilinks(vaull)

    # 3. MOC 文件
    moc = vaull / "读书脑图.md"
    if not moc.exists():
        # 创建初始 MOC
        type_info = TYPE_VAULT.get(type_code, {})
        mermaid_filename = type_info.get("mermaid", "类型化.mermaid.md")

        content = f"""---
title: 读书脑图
book: "{meta['title']}"
type: moc
created: {TODAY}
updated: {TODAY}
tags: [moc, {type_code}, {sub_name}]
---

# 《{meta['title']}》读书脑图

## 书籍信息

1. 作者：{meta.get('creator', '未知')}
2. 译者：(待填入)
3. 出版社：{meta.get('publisher', '未知')}
4. 出版年：(待填入)
5. ISBN：(待填入)
6. 页数：(待填入)
7. 原作名：(待填入)
8. **类型：{type_code} {sub_name}**
9. **字数：{format_word_count(meta['total_chars'])}**
10. 豆瓣评分：(待豆瓣数据嵌入后填入)

## 豆瓣数据

(待豆瓣数据嵌入后填入)

## 阅读方式 (7 种阅读法中必选 4-5 种)

(待 LLM 抽取后填入)

## 章节结构

(由 entities phase 自动填入)

## 涉及人物

(由 entities phase 自动填入)

## 核心概念

(由 entities phase 自动填入)

## 主题

(由 entities phase 自动填入)

## 关键摘录

(由 entities phase 自动填入)

## 阅读路径

### 阅读前
(由 LLM 抽取后填入)

### 阅读中
(由 LLM 抽取后填入)

### 阅读后
(由 LLM 抽取后填入)

## 关系图

[[{mermaid_filename.replace('.mermaid.md', '')}]]

## 附录

(由 LLM 抽取后填入)
"""
        write_file(moc, content)

    # 4. 自动补全 MOC 的入链 (避免 orphan)
    #    找到 MOC 文件中 "## 涉及人物" 段, 在它后面追加所有人物文件 wikilink
    text = moc.read_text(encoding="utf-8", errors="replace")

    # 找到人物/ 目录的所有文件
    people_dir = vaull / "人物"
    if people_dir.exists():
        people_files = sorted([f.stem for f in people_dir.glob("*.md")])
        # 在 MOC 找 "## 涉及人物" 段, 替换其内容
        people_block = "## 涉及人物\n\n" + "\n".join(
            [f"- [[{stem}]]" for stem in people_files]
        )
        text = re.sub(r'## 涉及人物.*?(?=\n## |\Z)',
                     people_block, text, flags=re.DOTALL)

    # 找到章节/ 目录的所有文件
    chapters_dir = vaull / "章节"
    if chapters_dir.exists():
        chapter_files = sorted([f.stem for f in chapters_dir.rglob("*.md")])
        chapter_block = "## 章节结构\n\n" + "\n".join(
            [f"- [[{stem}]]" for stem in chapter_files]
        )
        text = re.sub(r'## 章节结构.*?(?=\n## |\Z)',
                     chapter_block, text, flags=re.DOTALL)

    # 概念/ 主题/ 摘录 同理 (简化)
    for sub, header in [("概念", "核心概念"), ("主题", "主题"), ("摘录", "关键摘录")]:
        sub_dir = vaull / sub
        if sub_dir.exists():
            files = sorted([f.stem for f in sub_dir.glob("*.md")])
            block = f"## {header}\n\n" + "\n".join(
                [f"- [[{stem}]]" for stem in files]
            )
            text = re.sub(rf'## {header}.*?(?=\n## |\Z)',
                         block, text, flags=re.DOTALL)

    moc.write_text(text, encoding="utf-8")
    print(f"✓ Phase moc 完成: MOC 已更新, 含 {len(people_files) if people_dir.exists() else 0} 人物 + {len(chapter_files) if chapters_dir.exists() else 0} 章节 wikilink")


# ========================
# 主函数
# ========================

def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="book-vault-analysis: 构建完整 Obsidian vault"
    )
    parser.add_argument("vault", type=Path, help="Vault 路径")
    parser.add_argument("--phase", choices=["scaffold", "entities", "mermaid", "moc", "all"],
                        default="all", help="运行阶段")
    parser.add_argument("--type", default="T1", help="14 大类之一 (T1-T14)")
    parser.add_argument("--scratch", type=Path, default=None, help="Spine 抽取目录")
    # 内容注入 (LLM 生成的内容以 JSON 传入)
    parser.add_argument("--people-json", type=Path, default=None, help="人物档案 JSON")
    parser.add_argument("--concepts-json", type=Path, default=None, help="概念 JSON")
    parser.add_argument("--themes-json", type=Path, default=None, help="主题 JSON")
    parser.add_argument("--quotes-json", type=Path, default=None, help="摘录 JSON")
    parser.add_argument("--chapters-json", type=Path, default=None, help="章节笔记 JSON")
    parser.add_argument("--mermaid-content", type=Path, default=None, help="Mermaid 完整 markdown")
    parser.add_argument("--moc-content", type=Path, default=None, help="MOC 完整 markdown")

    args = parser.parse_args()

    vaull = args.vault
    phase = args.phase
    type_code = args.type
    sub_name = {"T1": "小说", "T2": "哲学", "T3": "方法论", "T4": "投资",
                "T5": "商业", "T6": "政经", "T7": "历史", "T8": "心理",
                "T9": "科普", "T10": "教育", "T11": "艺术", "T12": "育儿",
                "T13": "旅行", "T14": "混合"}.get(type_code, "小说")

    SCRATCH = args.scratch
    if SCRATCH is None:
        SCRATCH = Path.cwd() / "scratch" / vaull.name

    # 读取 metadata
    meta_path = SCRATCH / "metadata.json"
    if not meta_path.exists():
        print(f"错误: {meta_path} 不存在. 请先运行 s20_extract_epub_spine.py")
        sys.exit(1)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    # 读取 LLM 生成的内容 (如果提供)
    def load_json(path):
        if path is None:
            return None
        if not path.exists():
            print(f"警告: {path} 不存在, 跳过")
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_text(path):
        if path is None:
            return None
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    people_data = load_json(args.people_json)
    concepts_data = load_json(args.concepts_json)
    themes_data = load_json(args.themes_json)
    quotes_data = load_json(args.quotes_json)
    chapters_data = load_json(args.chapters_json)
    mermaid_content = load_text(args.mermaid_content)
    moc_content = load_text(args.moc_content)

    # 运行各 phase
    if phase in ("scaffold", "all"):
        phase_scaffold(vaull, type_code, sub_name, meta)
    if phase in ("entities", "all"):
        phase_entities(vaull, type_code,
                       people_data=people_data,
                       concepts_data=concepts_data,
                       themes_data=themes_data,
                       quotes_data=quotes_data,
                       chapters_data=chapters_data)
    if phase in ("mermaid", "all"):
        phase_mermaid(vaull, type_code, mermaid_content=mermaid_content)
    if phase in ("moc", "all"):
        phase_moc(vaull, type_code, sub_name, meta)

    if phase == "all":
        print("\n=== 完成 ===")
        print("vault 已生成, 运行 Step 9 验证:")
        print("  python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/s90_validate_vault.py '<书名>'")
        print("  python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/s95_check_placeholders.py <vault_path>")
        print("  python3 ~/.hermes/skills/productivity/book-vault-analysis/scripts/s96_finalize_vault.py <vault_path>")


if __name__ == "__main__":
    main()
