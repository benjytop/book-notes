# book-notes

Obsidian 书籍导读与分析

## 目录

- `2025/` - 2025 年读过的书
- `2026/` - 2026 年读过的书
- `SKILL/book-vault-analysis/` - book-vault-analysis skill
- `正在看/` - 正在读的书
- `需求池/` - 待处理的需求

## 工具

用 `book-vault-analysis` SKILL 分析每本书, 自动生成 Obsidian vault。
基础 SKILL 从 PRD 生成，后续为了节省 Token，将重复分析行为固化成 Script。
本仓库仅提供 Mac 版本，其他版本可以让 LLM 从 PRD 重新生成。

## SKILL 文件位置

`SKILL/book-vault-analysis/`

```
SKILL/book-vault-analysis/
├── PRD.md                              需求文档(PRD)
├── SKILL.md                            SKILL 说明
├── scripts/
│   ├── s20_extract_epub_spine.py       抽取 EPUB spine
│   ├── s30_classify_book.py            14 大类分类
│   ├── s40_fetch_douban_data.py        抓取豆瓣数据
│   ├── s50_build_vault.py              构建 vault (4 阶段)
│   ├── s90_validate_vault.py           L1 13-POINT 硬检查
│   ├── s95_check_placeholders.py       占位符检测
│   ├── s96_finalize_vault.py           L2 5 项软检查
│   └── s97_cross_book_validator.py     跨书内容污染检测
├── references/                         20 个参考文档
└── templates/                          14 个模板 (T1-T14)
```

## 14 大类图书分类

`book-vault-analysis` SKILL 把书分类到 14 大类之一, 不同类型生成不同的 vault 结构。

| ID | 类型 | 说明 |
|---|---|---|
| T1 | 文学 | 小说 / 散文 / 短篇集 |
| T2 | 思想史/哲学 | 思想史入门 / 名著导读 |
| T3 | 方法论/自助 | 学习方法 / 习惯养成 |
| T4 | 投资/经济 | 价值投资 / 宏观 / 经济史 |
| T5 | 商业/管理 | 创业 / 公司 / 管理 |
| T6 | 政经/时政 | 政治 / 政策 / 国际关系 |
| T7 | 历史/纪实 | 历史 / 传记 / 游记 |
| T8 | 心理/自助 | 心理学 / 自助成长 |
| T9 | 科普/科学 | 科普 / 科学 / 自然 |
| T10 | 教育/学习 | 教育理论 / 教学 |
| T11 | 艺术/设计 | 艺术 / 设计 / 美学 |
| T12 | 育儿/家庭 | 育儿 / 家庭关系 |
| T13 | 旅行/地理 | 旅行 / 地理 / 文化 |
| T14 | 混合 (跨大类) | 跨多个大类的书 |
