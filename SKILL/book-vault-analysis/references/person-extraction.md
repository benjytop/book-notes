# 人物抽取方法论 (Person Extraction)

> 从 `obsidian-vault-build/references/person-extraction.md` 迁移而来 (v1.0.0, 2026-07-21)

## 用户反馈驱动

> "我看了好几本书的人物关系，感觉人员都不全，并且有一些虚构的书作者是局外人身份并不在情节内有关系也被算进去了"

**翻译**: 不要只抽 5 个人, 要**大而全** (覆盖情节人物 + 出版关系); 也要**准确** (虚构的书作者是局外人身份不应该混进情节人物).

## 为什么这个重要

手选 5 个角色 = **快但有损**. jieba + co-occurrence = **自动但不同方式的有损**:

- 长篇小说 (追风筝的人, 灿烂千阳, 群山回唱) 有 20+ 有名字的重要角色.
- 作者/译者/出版社 经常被混入情节人物.
- "局外人"情况 (书里没出现作者) 仍被作为 "author" 链接.
- jieba 没有**语义理解**: 能告诉你 "哈桑 出现 498 次, 与 阿里 共现 61 次", 但不能标注关系类型 (**父子/师徒/夫妻/仇敌**) 或写叙事摘要.
- jieba 输出**只有实体列表** - 没有人物简介、关键事件、人物弧线.

**修复方案**:
1. **LLM-based 抽取 (默认, 优先)** - 读 EPUB, 输出有语义的人物 + 关系 + 叙事摘要
2. **jieba 流水线 (兜底)** - 仅在 LLM 不可用时使用

**默认新书: 用 LLM**.

## 双层模型

始终分离两种关系在不同的文件 / 不同的 Mermaid subgraphs:

| 层 | 内容 | 来源 |
|---|---|---|
| **情节人物 (Plot)** | 出现在叙事中的虚构人物 | LLM 读取 + jieba 共现 (统计用) |
| **出版关系 (Publishing)** | 作者, 译者, 编辑, 出版社 | EPUB `<dc:creator>`, `<dc:contributor>`, `<dc:publisher>` 元数据 |

在 Mermaid 中用**单独 subgraph** 渲染 (e.g. `subgraph Publishing` vs `subgraph ZL_family`), 或**单独 Mermaid 文件** if 用户要清晰的分割.

## LLM 抽取工作流 (默认, 2026-07-20+)

```
1. 读 EPUB spine (分块) (/tmp/literary-scratch/<书名>/spine/*.txt)
2. 浏览开头/中间/结尾的块, 建立心理模型
3. 生成 人物/<name>.md 每个主要人物 (200-500 字):
   - 简介 (身份, 家庭, 在书中的角色)
   - 关键事件 (按时间顺序的关键时刻)
   - 关键人物关系 (类型: 夫妻/父子/朋友/敌人/...)
   - 关联人物 (with co-occurrence counts if available)
4. 生成 人物关系图.mermaid.md:
   - subgraph 分组 (e.g. 出生家庭, 婚后家庭, 朋友)
   - 类型化边: -->|夫妻|, -->|家暴|, -->|私生|, -->|童年恋人/夫妻|
   - 颜色/样式: 主角红, 施暴者黑, 情人绿
5. 更新 MOC: type + comprehensive 涉及人物 列表
6. 验证: L1 + L2 必须 0 hard error
```

## 关键经验 (Pitfalls)

### 1. LLM 不要写 /tmp/build_*.py

直接用 skill 的 `s50_build_vault.py --phase=entities` + `--people-json=...` 注入.

用户反馈: "我以为把脚本固化到 skill 里的脚本里后就不需要生成什么脚本了"

### 2. 区分情节人物 vs 出版关系

- 作者/译者/出版社放一个 subgraph (`Publishing`)
- 虚构情节人物放另一个 subgraph (`ZL_family` 等)
- MOC 涉及人物段也分两节

### 3. 真实作者不要误删

```
# 胡赛尼 = Hosseini (灿烂千阳, 群山回唱, 追风筝的人 的真实作者)
# 林欣浩 = 哲学家们都干了些什么 的作者
```

不要用 `[` blanket-delete 文件名.

### 4. 人物简介 ≥ 200 字

L2 #2 short-note 检查: 自动生成的人物模板 < 200 字会 FAIL. 用模板 (元数据 + 占位段) 填充.

### 5. L1 orphan 检查

每个新 `人物/<name>.md` 必须有从 MOC `## 涉及人物` 段的入链. 生成完所有人物后, 重新跑 `s50_build_vault.py --phase=moc` 自动建立入链.

## Sample stats (2026-07-20, 16 books × book-notes/2025)

| 指标 | 值 |
|---|---|
| 总人物文件 | 686 |
| 共现对 | 2,068 |
| 主要人物 (top 12/本) | 150 |
| 配角 (top 30/本) | 536 |
| L1 + L2 通过率 | 16/16 |

## 这个方法不做什么

- 不抽取人物**弧线** (哪个章节出现, 说了什么/做了什么). 需要第二轮抽取 + 引文归属.
- 不抽取超越共现的语义关系 (没有 "是父亲", "杀害", "结婚" 语义抽取). 共现是代理, 不是真正的语义图.
- 不适用于非虚构 (政治家, 科学家). 用相同方法但名称来自前页索引, 不是 jieba posseg.

如果需要更丰富的数据, 下一步是接入真正的 NER 模型 (hanlp, stanza-zh, 或用户自己的字典). 对 90% 的中文文学书, jieba.posseg 够用.

---

**原 skill**: `obsidian-vault-build` v1.4.0 (references/person-extraction.md)
**迁移日期**: 2026-07-21
**迁移原因**: 清理冗余 skill, 保留关键方法论到主 skill 的 references/