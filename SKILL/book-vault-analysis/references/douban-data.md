# 豆瓣数据嵌入 (D1-D10)

10 个豆瓣数据处理规则。

## 规则清单

| # | 规则 | 触发 | 输出 |
|---|---|---|---|
| D1 | ISBN 直接跳转 | EPUB 有 ISBN | `/subject/<isbn>/` |
| D2 | 搜索兜底 | D1 失败 | `?search_text=<书名>+<作者>&cat=1001` |
| D3 | 用户 URL 优先 | 用户提供 URL | 直接用 |
| D4 | Top250 排名 | subject 在 Top250 | `No.88 豆瓣图书 Top250` |
| D5 | 评分分布 | 任意 | `5★ 58.5% / 4★ 34.3% / ...` |
| D6 | Top 5 短评精选 | 评价人数 ≥ 5 | ≤ 5 条 hot comments |
| D7 | 同译本搜索链接 | ≥ 2 同名 subject | `> 📚 豆瓣搜索 - <书名>: [链接]` |
| D8 | 同类型更高分提醒 | 候选中更高分 | `> ⚠️ 提示: [书名] (URL) 评分 X.X` |
| D9 | 内容简介/作者简介 | 任意 | 原文搬运, 不改写 |
| D10 | 嵌入 MOC | 任意 | `## 豆瓣数据` 段 |

## 实现

`s40_fetch_douban_data.py` 完整实现 D1-D10:

```python
def fetch_douban_data(book_title, author, isbn=None, user_url=None):
    # D1: ISBN direct
    if isbn:
        url = f"https://book.douban.com/isbn/{isbn}/"
        # ... fetch

    # D2: Search fallback
    search_url = f"https://search.douban.com/book/subject_search?search_text={quote(book_title + ' ' + author)}&cat=1001"
    # ... fetch

    # D3: User URL
    if user_url:
        url = user_url

    # D4-D5: Extract rating, distribution
    # D6: Hot comments (skip if 评价人数 < 5)
    # D7-D8: Multi-edition, higher-rating
    # D9: Content/author intros
    # D10: Return data dict
```

## MOC 嵌入模板

```markdown
## 豆瓣数据

> 通过 ISBN `<isbn>` 关联豆瓣条目

🔗 [豆瓣页面](<douban_url>)

**基本信息**

- 作者：[[卡勒德·胡赛尼]]
- 译者：[[李继宏]]
- 出版社：上海人民出版社 / 世纪文景
- 出版年：2007-9
- ISBN：9787208072107
- 页数：428 页
- 装帧：平装
- 定价：28.00 元
- 原作名：A Thousand Splendid Suns
- 丛书：卡勒德·胡赛尼作品

**豆瓣评分** 8.9 · 134,909 人评价
- 分布：5★ 58.5% / 4★ 34.3% / 3★ 6.7% / 2★ 0.4% / 1★ 0.1%
- 排名：**No.88 豆瓣图书 Top250**

### 内容简介

> <douban content_intro 原文>

### 作者简介

> <douban author_intro 原文>

### 短评精选

> **用户1**：<原文>
> **用户2**：<原文>
> **用户3**：<原文>
> **用户4**：<原文>
> **用户5**：<原文>
```

## 同译本搜索链接 (D7)

**触发条件**: 豆瓣搜索返回 ≥ 2 个同名 subject (title-match 验证)

**位置**: MOC 豆瓣数据段底部

**格式**:
```markdown
> 📚 豆瓣搜索 - <书名>：[在豆瓣查看所有版本](https://search.douban.com/book/subject_search?search_text=<urlencoded>&cat=1001)
```

## 同类型更高分提醒 (D8)

**触发条件**: 候选中评分更高的同类版本

**格式**:
```markdown
> ⚠️ 提示：豆瓣搜索到评分更高的同类版本（[<书名>](URL) 评分 X.X），建议考虑比较
```

**title-match 验证**: 用 `browser_navigate` 检查每个候选 `<h1>` 书名, 避免同名异书。
