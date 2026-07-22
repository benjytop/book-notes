"""
抓取豆瓣数据。

D1: ISBN 直接跳转
D2: 搜索兜底
D3: 用户 URL 优先
D4-D5: Top250 + 评分分布
D6: Top 5 短评精选 (评价人数 < 5 跳过)
D7: 同译本搜索链接
D8: 同类型更高分提醒
D9: 内容简介 + 作者简介
D10: 嵌入 MOC

⚠️ **重要约束**: 当豆瓣搜索失败 (返回 isbn=null, subject_id=0, rating=0,
    hot_comments=[]) 时, 调用方 **禁止**用训练记忆填补 MOC 字段.
    必须留 [待豆瓣数据嵌入后填入] 或 [豆瓣暂无数据] 占位.
    调用方必须用 scripts/s97_cross_book_validator.py <vault_path> <vault_type>
    二次验证类型错配.
    详见 references/llm-inference-pitfall.md.

用法:
    python3 s40_fetch_douban_data.py <书名> <作者> [ISBN] [豆瓣URL]

输出 JSON 到 stdout + 渲染后的 MOC 嵌入块 (D10).

注: 本 skill 的脚本在 Mac + Python 3 下开发验证。
    移植到其他平台可能需要小调整 (例如解释器名称)。
"""
import sys
import re
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def http_get(url: str, timeout: int = 15) -> str:
    """使用 urllib (避免依赖外部 curl 命令)."""
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except (URLError, HTTPError) as e:
        print(f"警告: HTTP 请求失败 {url}: {e}", file=sys.stderr)
        return ""


def fetch_search_results(title: str, author: str) -> list:
    """D2: 在豆瓣搜索候选 subject_id."""
    query = quote(f"{title} {author}")
    url = f"https://search.douban.com/book/subject_search?search_text={query}&cat=1001"
    html = http_get(url)
    ids = re.findall(r'subject/(\d+)', html)
    seen = set()
    unique = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            unique.append(i)
    return unique[:5]


def fetch_subject_data(subject_id: str) -> dict:
    """抓取豆瓣 subject 页面基本信息 (D4-D5)."""
    url = f"https://book.douban.com/subject/{subject_id}/"
    html = http_get(url)
    data = {"subject_id": subject_id, "url": url}

    if not html:
        return data

    # D5 评分 (property="v:average")
    m = re.search(r'property="v:average"[^>]*>\s*(\d+\.\d+)\s*</', html)
    if m:
        data["rating"] = float(m.group(1))

    # D5 评价人数 (property="v:votes")
    m = re.search(r'property="v:votes"[^>]*>\s*(\d+)\s*</', html)
    if m:
        data["rating_count"] = int(m.group(1))

    # 备用人评价
    if "rating_count" not in data:
        m = re.search(r'(\d+)人评价', html)
        if m:
            data["rating_count"] = int(m.group(1))

    # D4 Top250
    if "豆瓣图书Top250" in html:
        data["top250"] = True

    # 书名
    m = re.search(r'<title>([^<]+)</title>', html)
    if m:
        data["title"] = m.group(1).strip().split(" (豆瓣)")[0]

    return data


def fetch_hot_comments(subject_id: str) -> list:
    """D6: 抓取豆瓣短评 Top 5 (从 subject page comments block)."""
    url = f"https://book.douban.com/subject/{subject_id}/"
    html = http_get(url)
    comments = []

    pattern = r'<span class="short"[^>]*>([^<]+)</span>'
    matches = re.findall(pattern, html)

    for text in matches[:5]:
        text = text.replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
        text = text.replace("&lt;", "<").replace("&gt;", ">")
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 5:
            comments.append(text)

    return comments


def fetch_intro(subject_id: str) -> dict:
    """D9: 抓取内容简介 + 作者简介 + 出版信息."""
    url = f"https://book.douban.com/subject/{subject_id}/"
    html = http_get(url)
    data = {}

    # 内容简介 (新版: 抓取整个 intro div 内的所有 p 标签内容, 排除 "·" 装饰符)
    # 优先抓 "展开全部" 后的 .all 版本, 内容更完整
    all_match = re.search(r'<span class="all hidden">\s*<div>\s*<style[^>]*></style>\s*<div class="intro">\s*(.*?)</div>\s*</div>\s*</span>', html, re.DOTALL)
    if not all_match:
        all_match = re.search(r'<div class="intro">\s*(.*?)</div>', html, re.DOTALL)
    if all_match:
        intro_html = all_match.group(1)
        # 提取所有 <p> 标签内容, 排除只有 "·" 的装饰符
        paragraphs = re.findall(r'<p>([^<]*)</p>', intro_html)
        # 过滤: 排除 "·" 和空白
        clean_paragraphs = [p.strip() for p in paragraphs if p.strip() and p.strip() != '·']
        if clean_paragraphs:
            data["intro"] = " ".join(clean_paragraphs)[:2000]

    # 出版信息
    info_patterns = {
        "publisher": r'<span class="pl">出版社:</span>(.+?)(?=</span>|<br)',
        "pub_year": r'<span class="pl">出版年:</span>([^<]+)',
        "isbn": r'<span class="pl">ISBN:</span>([^<]+)',
        "pages": r'<span class="pl">页数:</span>\s*(\d+)',
        "binding": r'<span class="pl">装帧:</span>([^<]+)',
        "price": r'<span class="pl">定价:</span>([^<]+)',
    }
    for key, pattern in info_patterns.items():
        m = re.search(pattern, html)
        if m:
            val = m.group(1).strip()
            data[key] = val

    # 作者
    author_match = re.search(r'<span class="pl">作者:</span>(.+?)</span>', html, re.DOTALL)
    if author_match:
        author_html = author_match.group(1)
        authors = re.findall(r"<a[^>]*>([^<]+)</a>", author_html)
        if authors:
            data["douban_authors"] = [a.strip() for a in authors]

    return data


def build_douban_data(title: str, author: str, isbn: str = None, user_url: str = None) -> dict:
    """构建完整的豆瓣数据 dict (D1-D10).

    Args:
        title: 书名
        author: 作者
        isbn: ISBN (可选, 用于 D1)
        user_url: 用户提供的豆瓣 URL (可选, 用于 D3)

    Returns: dict with fields:
        - title, author, isbn
        - douban_url
        - search_candidates
        - selected_subject_id
        - rating, rating_count, top250
        - multi_edition, multi_edition_search_url
        - hot_comments
    """
    data = {
        "title": title,
        "author": author,
        "isbn": isbn,
    }

    # D3: 用户 URL 优先
    if user_url:
        data["douban_url"] = user_url
        m = re.search(r'subject/(\d+)', user_url)
        if m:
            data["selected_subject_id"] = m.group(1)
            data["subject_id"] = m.group(1)
            subject_data = fetch_subject_data(m.group(1))
            data.update(subject_data)
        return data

    # D1: ISBN 直接
    if isbn:
        data["douban_url"] = f"https://book.douban.com/isbn/{isbn}/"
        return data

    # D2: 搜索
    candidates = fetch_search_results(title, author)
    data["search_candidates"] = candidates

    if not candidates:
        return data

    data["douban_url"] = f"https://book.douban.com/subject/{candidates[0]}/"
    data["selected_subject_id"] = candidates[0]

    # D4-D5: 抓取基本信息
    subject_data = fetch_subject_data(candidates[0])
    data.update(subject_data)

    # D7: 同译本链接 (≥ 2 同名)
    if len(candidates) >= 2:
        data["multi_edition_search_url"] = (
            f"https://search.douban.com/book/subject_search?"
            f"search_text={quote(title)}&cat=1001"
        )
        data["multi_edition"] = True
    else:
        data["multi_edition"] = False

    # D8: 同类型更高分 (简化版, TODO: 实际对比)
    data["higher_rating_alternative"] = None

    return data


def render_moc_douban_block(data: dict) -> str:
    """D10: 把豆瓣数据 dict 渲染成 MOC 嵌入 markdown.

    Returns: 完整的 "## 豆瓣数据" 段 markdown.
    """
    lines = []
    lines.append("## 豆瓣数据")
    lines.append("")

    # 链接
    url = data.get("douban_url")
    if url:
        lines.append(f"🔗 [豆瓣页面]({url})")
    multi_url = data.get("multi_edition_search_url")
    if multi_url:
        lines.append(f" | 🔗 [同译本搜索]({multi_url})")
    lines.append("")

    # 内容简介
    intro = data.get("intro")
    if intro:
        lines.append("### 内容简介")
        lines.append("")
        lines.append(f"> {intro}")
        lines.append("")

    # 作者
    authors = data.get("douban_authors", [])
    if authors:
        lines.append("### 作者简介")
        lines.append("")
        lines.append(f"> 作者: {', '.join(authors)}")
        lines.append("")

    # 短评
    comments = data.get("hot_comments", [])
    if comments:
        lines.append("### 短评精选 (豆瓣真实短评)")
        lines.append("")
        for i, c in enumerate(comments[:5], 1):
            text = c if isinstance(c, str) else c.get("text", str(c))
            lines.append(f'> **短评 {i}**: "{text}"')
            lines.append(">")
        if url:
            lines.append(f"> 🔗 [完整短评]({url}comments)")
        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("用法: python3 s40_fetch_douban_data.py <书名> <作者> [ISBN] [豆瓣URL]")
        sys.exit(1)

    title = sys.argv[1]
    author = sys.argv[2]
    isbn = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("http") else None
    user_url = None
    for arg in sys.argv[3:]:
        if arg.startswith("http"):
            user_url = arg

    data = build_douban_data(title, author, isbn, user_url)

    # D6: 短评精选 (评价人数 < 5 跳过)
    sid = data.get("selected_subject_id") or data.get("subject_id")
    rating_count = data.get("rating_count", 0)
    if rating_count < 5 or not sid:
        data["hot_comments"] = []
    else:
        data["hot_comments"] = fetch_hot_comments(sid)

    # D9: 内容简介 + 作者简介
    if sid:
        intro_data = fetch_intro(sid)
        data.update(intro_data)

    # D10: 渲染 MOC 嵌入块
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("\n--- 渲染后的 MOC 嵌入块 (D10) ---")
    print(render_moc_douban_block(data))


if __name__ == "__main__":
    main()