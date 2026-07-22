"""
抽取 EPUB spine 到临时目录的 spine/ 子目录。
供 book-vault-analysis skill 使用。

参数:
  <EPUB_PATH>  EPUB 文件路径
  <SCRATCH_DIR> 临时工作目录 (脚本会创建 spine/ 子目录)

用法:
    python3 s20_extract_epub_spine.py <EPUB_PATH> <SCRATCH_DIR>

不修改原 EPUB (只读契约)。

注: 本 skill 的脚本在 Mac + Python 3 下开发验证。
    移植到其他平台可能需要小调整 (例如解释器名称)。
"""
import sys
import re
import json
import zipfile
from pathlib import Path
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    """HTML 解析器, 提取可见文本, 保留段落结构。"""

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0  # 跳过 script/style 内容

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        # 块级元素强制换行
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def extract(epub_path: Path, scratch_dir: Path) -> dict:
    """
    抽取 EPUB 到 spine 文件。返回元数据字典。
    """
    scratch_dir.mkdir(parents=True, exist_ok=True)
    spine_dir = scratch_dir / "spine"
    spine_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(epub_path) as z:
        # 查找 OPF 文件
        opf_files = [n for n in z.namelist() if n.endswith('.opf')]
        if not opf_files:
            raise ValueError(f"EPUB 中找不到 OPF 文件: {epub_path}")
        opf_path = opf_files[0]
        opf = z.read(opf_files[0]).decode('utf-8', errors='replace')
        base_dir = opf_path.rsplit('/', 1)[0] if '/' in opf_path else ""

        # 解析 items (href 可能在 id 前面或后面)
        items = re.findall(r'<item\s+href="([^"]+)"\s+id="([^"]+)"', opf)
        if not items:
            items = re.findall(r'<item\s+id="([^"]+)"\s+href="([^"]+)"', opf)
            items = [(h, i) for i, h in items]
        id2href = {item_id: href for href, item_id in items}

        # 解析 spine 顺序
        spine_ids = re.findall(r'<itemref[^>]+idref="([^"]+)"', opf)

        # 提取元数据
        title_m = re.search(r'<dc:title[^>]*>([^<]+)</dc:title>', opf)
        creator_m = re.search(r'<dc:creator[^>]*>([^<]+)</dc:creator>', opf)
        creators_all = re.findall(r'<dc:creator[^>]*>([^<]+)</dc:creator>', opf)
        publisher_m = re.search(r'<dc:publisher[^>]*>([^<]+)</dc:publisher>', opf)
        contributors = re.findall(r'<dc:contributor[^>]*>([^<]+)</dc:contributor>', opf)
        identifier_m = re.search(r'<dc:identifier[^>]*>([^<]+)</dc:identifier>', opf)

        # 抽取每个 spine 文件
        chapter_count = 0
        total_chars = 0
        for idx, sid in enumerate(spine_ids, 1):
            href = id2href.get(sid)
            if not href:
                continue
            full = f"{base_dir}/{href}" if base_dir else href
            try:
                x = z.read(full).decode('utf-8', errors='replace')
            except Exception:
                continue
            parser = TextExtractor()
            parser.feed(x)
            text = "".join(parser.parts).strip()
            # 标准化空白
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text)
            if text:
                # 文件名: spine_NNN-slug.txt
                slug = re.sub(r"\W+", "_", href.rsplit("/", 1)[-1].rsplit(".", 1)[0])[:50]
                (spine_dir / f"spine_{idx:03d}-{slug}.txt").write_text(text, encoding="utf-8")
                chapter_count += 1
                total_chars += len(text)

    metadata = {
        "title": title_m.group(1) if title_m else None,
        "creator": creator_m.group(1) if creator_m else None,
        "creators_all": creators_all,
        "publisher": publisher_m.group(1) if publisher_m else None,
        "contributors": contributors,
        "identifier": identifier_m.group(1) if identifier_m else None,
        "spine_count": chapter_count,
        "total_chars": total_chars,
    }
    (scratch_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return metadata


def main():
    if len(sys.argv) < 3:
        print("用法: python3 s20_extract_epub_spine.py <EPUB_PATH> <SCRATCH_DIR>")
        sys.exit(1)

    epub_path = Path(sys.argv[1])
    scratch_dir = Path(sys.argv[2])

    if not epub_path.exists():
        print(f"错误: EPUB 文件不存在: {epub_path}")
        sys.exit(1)

    print(f"正在抽取: {epub_path.name}")
    meta = extract(epub_path, scratch_dir)
    print(f"  书名: {meta['title']}")
    print(f"  作者: {meta['creator']}")
    print(f"  出版社: {meta['publisher']}")
    print(f"  spine: {meta['spine_count']} 个文件, {meta['total_chars']:,} 字符")
    print(f"  保存到: {scratch_dir}")


if __name__ == "__main__":
    main()
