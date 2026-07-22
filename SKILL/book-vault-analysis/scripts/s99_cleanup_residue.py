"""
清理 vault 中 jieba 残留。

删除:
- 人物/<name>.md 中 <name> 是 jieba 噪声的文件
- calibre 软件残留
- 标有 jieba 标记的 人物关系图.mermaid.md
- 任何 .md 中的 broken wikilink

用法:
    python3 s99_cleanup_residue.py [VAULT_ROOT]

参数:
    VAULT_ROOT  vault 父目录 (例如: <VAULT_PARENT>/2025/)
               省略时使用当前目录 (CWD)

清理 vault 中 jieba 残留。
"""
import sys
import re
from pathlib import Path


# jieba 噪声词 (单字, 地名, 虚词等)
JIEBA_NOISE = {
    "卫峰", "吕新", "吕旷", "小婕", "老居士", "希曼", "弗斯", "修正",
    "卢曼", "塞进", "尼克", "公允", "加尔", "威廉", "孔雀", "卫东",
    "叶子", "乔治", "凯勒", "令堂", "玛丽", "玛尼", "多玛", "丹尼",
    "侯爵", "佐罗", "呼唤", "但凡", "亚当", "伯克", "卫星", "双赢",
    "博客", "坎特", "宁静", "妮拉", "尔瓦", "巴格", "布尔", "关陇",
    "安逸", "安静", "丁元英", "伯爵", "叶晓", "柏林", "王明", "秦谷",
    "肖亚", "卫", "峰", "吕", "新", "旷", "婕", "希", "曼", "弗",
    "斯", "修", "塞", "加尔", "威", "廉", "孔", "雀", "乔", "治",
    "凯", "东", "叶", "令", "堂", "公", "正", "养", "老", "埃",
    "尔", "丹", "尼", "侯", "爵", "卢", "但", "凡", "佐", "罗",
    "呼", "唤", "外", "婆", "亚", "当", "伯", "克", "卫", "星",
    "双", "赢", "博", "客", "坎", "特", "宁", "静", "宝", "典",
    "妮", "拉", "尔", "瓦", "巴", "格", "布", "尔", "关", "陇",
    "安", "逸", "静", "丁", "元", "英", "伯", "爵", "叶", "晓",
    "柏", "林", "古兰经", "古老", "察曼", "玛丽雅", "张开", "里克",
    "毛拉", "和塔", "和努尔", "哈姆", "哈拉", "拉赫", "布卡", "卡迪姆",
    "阿卜杜拉", "萨伊德", "赫拉特", "艾哈迈德", "纳吉布拉", "胡赛尼",
    "阿里", "马苏德", "古尔德", "塞夫", "拉辛", "塞莱", "斯",
    "塔吉克", "沙纳玛", "罗斯坦", "梁", "人物", "心理", "子女", "妹妹",
    "图勒", "海德尔", "马林", "普什图", "塔利班", "阿富汗", "阿富汗人",
    "哈扎拉", "白沙瓦", "卡林", "米拉", "瓦希德", "卡比尔", "欧瑟",
    "卡塞姆", "瓦里", "加兹", "卡莫", "霍玛勇", "莎娜", "贾拉",
    "拉巴特", "费萨尔", "弗里", "安德鲁", "阿克巴", "奥马尔", "阿曼",
    "瓦兹尔", "宝丽莱", "塔勒", "简言之", "范畴", "智慧", "宝贵",
    "宝石", "承前启后", "令人", "容易", "罗辑", "简单", "利他",
    "诺亚", "海明威", "雨果", "老舍", "国画", "传习录", "克氏",
    "亚里", "保罗", "伽里玛", "怀特海", "亚里士多德", "加缪", "让",
    "波普尔", "查尔斯", "蒙田", "歌德", "弗洛姆", "鲍曼", "阿伦特",
    "马尔库塞", "罗尔斯", "哈贝马斯", "福柯", "亨廷顿", "哈耶克",
    "基佐", "霍尔", "戴蒙德", "雅法", "阿马蒂亚", "海德格尔", "什",
    "宋", "黄", "人", "进", "出", "来", "时", "高低", "酸甜苦辣",
    "哭泣", "乌托邦", "古今", "古今之", "关怀", "亨廷顿", "莫尔",
    "和子", "卓越", "克拉斯", "塔勒布", "老爷", "塔勒先生",
}

# 出版关系 (永远保留)
PUBLISHING = {
    "卡勒德·胡赛尼", "李继宏", "康慨", "赵灿", "林欣浩", "刘擎",
    "蒂姆·费里斯", "樊登", "纳瓦尔·拉维坎特", "埃里克·乔根森",
    "霍华德·马克斯", "刘建位", "姚翔", "姚海军", "胡允桓",
    "黄锦秋", "张玉花", "姚向辉", "姚洋", "陈嘉映", "梁文道",
    "六六", "常劲", "本杰明·格雷厄姆", "沃伦·巴菲特", "查理·芒格",
    "李录", "阿瑟·克拉克", "海因里希", "迈克尔·刘易斯", "纳西姆",
    "加缪", "加斯东", "柏拉图", "纳瓦尔", "上海人民出版社",
    "作家出版社", "世纪文景", "中信出版社", "中信出版集团",
    "大", "方", "芒格书院", "三联书店", "果麦", "译林出版社",
    "天津人民", "人民邮电出版社", "北京日报出版社", "北京日报",
    "机械工业出版社", "中国友谊出版公司", "中国人民大学出版社",
    "清华大学出版社", "湛庐文化", "湛庐", "现代出版社",
    "南海出版公司", "南海出版", "上海文艺出版社", "南海", "现代",
    "阿勒特·德·圣埃克苏佩里", "安东尼·德·圣-埃克苏佩里",
    "圣埃克苏佩里", "上海译文出版社", "上海译文", "卡勒德",
}

# calibre 软件生成的文件名模式
CALIBRE_PATTERN = re.compile(r"^calibre\s*\([^)]+\)\s*\[.*\]$", re.IGNORECASE)


def is_publishing(name: str) -> bool:
    """判断是否为出版关系 (作者/译者/出版方)。"""
    if name in PUBLISHING:
        return True
    if "出版社" in name or any(kw in name for kw in ["文汇", "经典", "中译", "出版"]):
        return True
    return False


def is_calibre(name: str) -> bool:
    """判断是否为 calibre 软件残留。"""
    return bool(CALIBRE_PATTERN.match(name))


def clean_vault(vault: Path) -> int:
    """清理单个 vault, 返回删除的文件数。"""
    if not vault.exists():
        return 0

    count = 0
    chars_dir = vault / "人物"
    if chars_dir.exists():
        for f in list(chars_dir.glob("*.md")):
            # 删除非出版关系的文件
            if not is_publishing(f.stem) or is_calibre(f.stem):
                f.unlink()
                count += 1
        # 删除 calibre 残留
        for f in list(vault.rglob("*")):
            if f.is_file() and is_calibre(f.stem):
                f.unlink()
                count += 1

    # 删除 jieba 模板文件 (仍含 jieba 文本)
    if chars_dir.exists():
        for f in list(chars_dir.glob("*.md")):
            if is_publishing(f.stem):
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            if "jieba" in text.lower() or "co-occurrence" in text.lower():
                f.unlink()
                count += 1

    # 删除 jieba 模板的 人物关系图
    rel_fig = vault / "人物关系图.mermaid.md"
    if rel_fig.exists():
        content = rel_fig.read_text(encoding="utf-8", errors="replace")
        if "co-occurrence" in content or "auto-extracted, jieba" in content:
            rel_fig.unlink()
            count += 1

    # 清理 MOC wikilink
    moc = vault / "读书脑图.md"
    if moc.exists():
        text = moc.read_text(encoding="utf-8", errors="replace")
        orig = text
        for noise in JIEBA_NOISE:
            text = re.sub(r'\s*/?\s*\[\[' + re.escape(noise) + r'\]\]', '', text)
        text = re.sub(r' / / ', ' / ', text)
        text = re.sub(r'\[\[/\]\]', '', text)
        if text != orig:
            moc.write_text(text, encoding="utf-8")

    return count


def main():
    # 默认使用当前目录 (CWD)
    if len(sys.argv) > 1:
        vault_root = Path(sys.argv[1])
    else:
        vault_root = Path.cwd()

    if not vault_root.exists():
        print(f"VAULT_ROOT 不存在: {vault_root}")
        sys.exit(1)

    print(f"正在清理 vaults: {vault_root}")
    total = 0
    for vault in sorted(vault_root.iterdir()):
        # 跳过备份目录 (以 _backup 结尾或包含 backup 字样)
        if not vault.is_dir() or vault.name == ".obsidian":
            continue
        if "_backup" in vault.name.lower() or "backup" in vault.name.lower():
            continue
        n = clean_vault(vault)
        if n > 0:
            print(f"  {vault.name}: 删除 {n} 个文件")
        total += n
    print(f"\n总计: 删除 {total} 个文件")


if __name__ == "__main__":
    main()
