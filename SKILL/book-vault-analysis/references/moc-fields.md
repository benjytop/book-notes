# MOC 字段顺序 (Mandatory)

`读书脑图.md` 必须按以下顺序包含 10 个字段。

## 字段顺序表

| # | 字段 | 必含 | 说明 |
|---|---|---|---|
| 1 | 作者 | ✓ | 原名/中译名 |
| 2 | 译者 | ✗ (如有) | 仅外文译著 |
| 3 | 出版社 | ✓ | |
| 4 | 出版年 | ✓ | 格式 `2007-9` |
| 5 | ISBN | ✓ | 13 位 |
| 6 | 页数 | ✓ | 数字 |
| 7 | 原作名 | ✗ (如有) | 仅外文译著 |
| 8 | **类型** | ✓ | `T1 文学 - 小说` |
| 9 | **字数** | ✓ | `21.6 万字` (C12 规则) |
| 10 | 豆瓣评分 | ✗ (建议) | `8.9 / 134,909 人评价` |

## 模板

```markdown
## 书籍信息

1. 作者：[美] 卡勒德·胡赛尼
2. 译者：李继宏
3. 出版社：上海人民出版社 / 世纪文景
4. 出版年：2007-9
5. ISBN：9787208072107
6. 页数：428
7. 原作名：A Thousand Splendid Suns
8. **类型：T1 文学 - 小说** (长篇小说, 女性命运, 阿富汗题材)
9. **字数：21.6 万字**
10. 豆瓣评分：8.9 / 134,909 人评价
```

## 实现

`s50_build_vault.py` 自动按上述顺序写入, 不依赖人工:

```python
book_info_lines = [
    f"1. 作者：{metadata['author']}",
    f"2. 译者：{metadata['translator']}" if metadata.get('translator') else None,
    f"3. 出版社：{metadata['publisher']}",
    f"4. 出版年：{metadata['pub_year']}",
    f"5. ISBN：{metadata['isbn']}",
    f"6. 页数：{metadata['pages']}",
    f"7. 原作名：{metadata['original_name']}" if metadata.get('original_name') else None,
    f"8. **类型：{type_code} {type_name} - {sub_name}** ({description})",
    f"9. **字数：{word_count}**",
    f"10. 豆瓣评分：{douban_rating} / {douban_count} 人评价" if douban_rating else None,
]
```

## MOC 标准结构 (10 sections)

```
## 书籍信息         (10 字段)
## 豆瓣数据         (Douban block)
## 阅读方式         (4-5 必选阅读法)
## 章节结构         (51 章 wikilink 列表)
## 涉及人物 (或 思想家/概念) (类型化)
## 核心概念         (5 entries)
## 主题            (5 entries)
## 关键摘录         (5 entries)
## 阅读路径         (pre/mid/post)
## 关系图          (Mermaid inbound link)
```

每节必须存在 (即使内容很短)。`s50_build_vault.py` 强制生成。
