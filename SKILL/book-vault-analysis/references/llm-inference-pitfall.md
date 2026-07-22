# LLM 推断陷阱 (LLM Inference Pitfalls)

> **问题**: 当 `s40_fetch_douban_data.py` 抓取豆瓣数据失败 (豆瓣屏蔽, 返回 `isbn: null`, `subject_id` 缺失) 时, LLM 会用**训练记忆**"推断"作者和背景, 经常出现**跨书内容污染** (e.g. 把书 A 错填为作者 B 的作品, 引用作者 B 的元素).

---

## 🚨 根因

LLM 在以下场景下"自信偏见" 高发:
- 训练记忆强项 (知道某作者写过某作品)
- 同一 session 内"上下文污染" (用户最近分析过的作家)
- 豆瓣数据缺失时, LLM 用记忆填空

**唯一可靠的作者识别信号**: spine 后记中的作者自述 + OPF metadata + 真实的豆瓣数据.

---

## ✅ 强制规则 (5 条)

1. **豆瓣数据失败 = 数据缺失, 不是推断**.
   当 `isbn`/`subject_id`/`rating`/`hot_comments` 任一缺失时, MOC 的作者/译者/出版社/出版年/ISBN/页数/原作名/字数/豆瓣评分字段必须留 `[待豆瓣数据嵌入后填入]` 或 `[豆瓣暂无数据]`, **不写猜测**.

2. **作者和场景必须从 spine 内容推断**, 不从训练记忆.
   - 读 `/tmp/literary-scratch/<书名>/spine/*.txt` 找城市名/关键人物/后记作者自述
   - 读 `/tmp/literary-scratch/<书名>/metadata.json` 看 OPF dc:creator/dc:title

3. **严禁"风格延续假设"**.
   如果用户之前分析过同作者另一本, LLM 不能把作者风格套到新书上.

4. **严禁"同主题推断作者"**.
   同主题不代表同作者 (例如所有动物故事不都是蔡崇达写的).

5. **检测**: 在 vault 生成后, 用 `scripts/s97_cross_book_validator.py <vault_path> T1` 等检查类型错配. 该脚本只检查"非本书类型" 的高频术语, 不硬编码具体作者元素.

---

## 🔍 通用检测规则

`scripts/s97_cross_book_validator.py` 是**通用**检测工具, 不依赖特定作者/作品的硬编码黑名单. 规则:

- **类型错配**: T1 文学 vault 不应出现 T4 投资术语 (橡树资本/钟摆), T2 思想史 vault 不应高频出现 T6 政经术语等.
- **同作者豁免**: 在 `exclude_books` 中列出的书名会豁免 (因为这些书合理引用其他作者/作品).
- **配置化**: 用户可在 `TYPE_FORBIDDEN_PATTERNS` 字典中添加自定义规则.

**工作流**:
```bash
python3 scripts/s97_cross_book_validator.py "<vault_path>" "<vault_type>"
# e.g. python3 s97_cross_book_validator.py "仙症" T1
# 应该输出: ✅ no type-mismatch pollution detected
```

---

## 📋 用户修复流程

如果用户报告 vault 错误:

1. **读取 spine 内容**: 找作者后记中的真实自述
2. **删除错误的实体** (旧作者/场景元素)
3. **创建正确实体** (新作者/真实场景)
4. **更新 MOC** (作者/简介/豆瓣 URL)
5. **重跑 L1 + L2 + Placeholder 验证**
6. **跑 s97_cross_book_validator.py** 二次确认

---

## 🎯 预防措施 (设计层)

### 1. build script 加警示注释

```python
"""
警示: 本书的作者必须从 spine 后记或 OPF metadata 提取.
如果 s40_fetch_douban_data.py 返回 isbn=null, subject_id=0,
说明豆瓣搜索失败, **禁止**用训练记忆填作者.

正确做法:
- 读 spine/spine_LAST.txt (后记)
- 读 metadata.json (OPF metadata)
- 如都失败, 留 [豆瓣暂无数据] 占位
"""
```

### 2. PRD.md 加约束

> **Section D0 (新增)**: 当豆瓣数据缺失时, MOC 必须留 `[豆瓣暂无数据]`, **严禁**用训练记忆填作者.

### 3. s97 自动检测

每次分析新书后, **必须**:

```bash
python3 scripts/s97_cross_book_validator.py "<vault_path>" T{N}
# 应该输出: ✅ no type-mismatch pollution detected
```

---

## 💡 经验教训

1. **LLM 在训练记忆强项上有"自信偏见"**: LLM 倾向把相似主题的新书归到训练记忆强的作者名下.
2. **同 session 内的"上下文污染"**: 最近分析过的作家会"高亮", LLM 倾向用同作者填充.
3. **豆瓣数据是唯一可靠信号**: 没有豆瓣数据, LLM 应该承认不知道, 而不是猜.
4. **spine 后记是最强信号**: 中文短篇集通常有作者后记, 自述生平, 是最可靠的作者识别源.

---

## ✅ 修复验证清单

每次分析新书后, **必须**:

- [ ] MOC 书籍信息的 `作者` 字段与豆瓣/OPF 一致
- [ ] `关联作品` 字段只列**同一作者**的其他作品
- [ ] `地点` 字段与 spine 内容的城市名匹配
- [ ] `人物` 字段在 spine 中能找到首次出现
- [ ] 不出现其他作者的"风格延续" 元素
- [ ] `python3 scripts/s97_cross_book_validator.py "<vault_path>" T{N}` 输出 `✅ no type-mismatch pollution detected`

---

## 🔗 相关

- `references/l1-l2-pitfalls.md` - L1/L2 检查中已知的边角问题
- `references/poc-experience.md` - 早期 POC 经验
- `references/douban-data.md` - D1-D10 豆瓣数据规范
- `scripts/s97_cross_book_validator.py` - 自动检测脚本 (类型错配)