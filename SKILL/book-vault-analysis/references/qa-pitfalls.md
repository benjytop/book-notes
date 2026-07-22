# QA Pitfalls (L1/L2 校验陷阱)

> 从 `obsidian-vault-qa-pitfalls` skill 迁移而来 (v1.0.0, 2026-07-21)

---

# obsidian-vault-qa-pitfalls

## 何时用

当你刚生成一个 Obsidian book vault, L1 / L2 校验器 (`validate_vault.py`, `finalize_vault.py`, `check_placeholders.py`) 报错时, 按本 skill 的优先级列表逐项修复. 不是改生成脚本, 是修 vault 里的具体问题.

**不适用**: 重写 skill / 重写生成流程 / 改 validator 本身. 这些用 `book-vault-analysis` skill.

## 优先级 1: Mermaid 解析失败 (L1 #12)

**症状**: `Mermaid parses: FAIL` + `Parse error on line N`

**最常见根因**: 中文 parens `(中文)` in node labels / edge labels / subgraph names. Mermaid parser 不接受中文括号.

**修复模式**:
```bash
# 找问题
grep -n "[" /vault/人物关系图.mermaid.md | head
# 修复
sed -i.bak 's/|父子 (名义)|/|名义父子|/g' /vault/人物关系图.mermaid.md
```

**不破坏的**:
- 双引号 `"中文 (内容)"` (parser 接受)
- `subgraph 名称 "中文 (内容)"` (用引号)
- 节点标签 `[中文]` (无 parens)

## 优先级 2: 占位符残留 (L1 #8 / L2 #5 / check_placeholders.py)

**症状**: `L1 #8 FAIL (X files)` 或 `L2 [5] ! N unfilled placeholder(s)`

**检测的 10 类** (完整 regex 见 `book-vault-analysis/references/placeholder-detection.md`):
1. `(待 X 填入)` - skill 模板
2. `(由 LLM...填入)` - 老式
3. `(由 X 填入)` - 通用
4. `(由 Step X 填入)` - 老式
5. `(Step X 填入)` - 老式
6. `(由 author_intro 填入)` - 豆瓣
7. `(由 content_intro 填入)` - 豆瓣
8. `(由 douban 填入)` - 豆瓣 (i)
9. `(LLM 内容生成填入)` - 老式
10. (MOC 模板: `(待 X 抽[取/填入])`)

**修复策略**:
- skill scaffold 创建的占位符 = 中间状态 (OK)
- 最终 vault = 必须替换
- 修复方向: 重跑 LLM 内容抽取, 用 `build_vault.py --phase=entities --people-json=...` 注入

**不能简单删除**: 删了之后文件变成"空短", L1 #9 会 FAIL.

## 优先级 3: Broken wikilinks (L1 #10)

**症状**: `Broken wikilinks FAIL (N unique: ['X', 'Y'])`

**5 类常见根因** (按频率):

### 3.1 Prefix 错位
- 错误: `[[人物-玛丽雅姆]]`
- 正确: `[[玛丽雅姆]]` (文件是 `人物/玛丽雅姆.md`, stem 无前缀)
- 检测: `grep -rn "\[\[人物-\|\[\[概念-\|\[\[主题-\|\[\[事件-" /vault/*.md`
- 修复: `sed -i '' 's/\[\[人物-/\[\[/g' /vault/*.md /vault/**/*.md`

### 3.2 Path-style wikilink
- 错误: `[[1-第一章/00-前言-XXX]]`
- 正确: 转换为 `**目录名/**` (Obsidian wikilink 不支持路径)
- 修复: skill 的 `build_vault.py --phase=moc` 自动处理

### 3.3 主题- prefix 缺失
- 错误: `[[友谊与背叛]]`
- 正确: `[[主题-友谊与背叛]]` (文件是 `主题/主题-友谊与背叛.md`)
- 检测: `grep -rn "^\[\[友谊与背叛\]\]" /vault/`
- 修复: `sed -i '' 's/\[\[友谊与背叛\]\]/[[主题-友谊与背叛]]/g' /vault/*.md /vault/**/*.md`

### 3.4 NN- 前缀未去
- 错误: `[[00-封面]]` `[[01-导言-评论]]`
- 正确: `[[封面]]` `[[导言-评论]]` (root 文件不应有 NN- 前缀)
- 检测: `grep -rn "00-\|01-" /vault/*.md | grep "实体wikilink"`
- 修复: rename files + sed wikilinks

### 3.5 跨 vault 引用
- 错误: MOC 里 `[[玛丽雅姆]]` (属其他书)
- 正确: 用纯文字 "玛丽雅姆 (《灿烂千阳》)"
- 检测: `grep -rn "\[\[" /vault/ | grep "已知其他书角色"`
- 修复: 替换为纯文字

## 优先级 4: Orphans (L1 #11)

**症状**: `Orphans FAIL (N files: ['X', 'Y'])`

**根因**: 文件存在但 MOC `读书脑图.md` 没有 wikilink 到它.

**3 类常见 orphan**:

### 4.1 根文件 orphan
- 缺 `README`, `封面`, `导言-评论`, `无剧透导读`, `全书结构`, `章节地图`, `主题与核心观点`, `复习卡片`, `阅读问题` 在 MOC 中
- 修复: 在 MOC 末尾"## 附录"段添加 wikilink 列表

### 4.2 实体 orphan
- 缺 `人物/`, `概念/`, `主题/`, `摘录/` 下的具体文件
- 修复: 在 MOC 对应段 (## 涉及人物 / ## 核心概念 / ## 主题 / ## 关键摘录) 添加

### 4.3 Mermaid orphan
- 缺 `<类型>图.mermaid.md` 在 MOC 中
- 修复: MOC 末尾"## 关系图"段添加 `[[人物关系图.mermaid]]` (注意保留 .mermaid 后缀)

**最常见**: skill 修复循环覆盖了 MOC 后, 删除了根文件链接. 解决方法: 重跑 `build_vault.py --phase=moc` 后, 手动添加 附录 + 关系图 段.

## 优先级 5: Empty/short notes (L1 #9)

**症状**: `no empty/short notes FAIL (N files)`

**根因**: scaffold 创建的占位文件, 内容只有 frontmatter + 占位符

**修复**: 重跑 Step 6 实体抽取, 或手动填充内容 (每文件 ≥ 200 字符)

## 优先级 6: 修复循环中的回归

**场景**: 修完一项, 又触发另一项

**典型链路**:
1. 修 wikilink → MOC 内容变 → 触发 placeholder 检测
2. 修 placeholder → scaffold 重写 → 又变 orphan
3. 修 orphan → MOC 内容变 → 又触发 wikilink

**对策**:
- 用 `check_placeholders.py` 单独跑 placeholder (避免触发其他检查的修复)
- 修完用 `validate_vault.py` 跑一遍, 记录所有 FAIL
- 然后按 P1 → P6 顺序逐项修
- 不用 skill 自动修复 (`build_vault.py --phase=moc` 会覆盖手工修改)

## 经验教训 (2026-07-21)

**真实案例**: 处理 16 本 + 2 本 vault 时, 每次都遇到相似的修复循环. 平均每本 5-10 分钟修复时间.

**根因分析**:
1. **生成脚本不完美** - 我的 part1/part2/part3 脚本有几处 bug (主题 prefix, mermaid parens, MOC links)
2. **skill 自动修复不完整** - 只修 4 类常见问题 (path, prefix, MOC), 不修 mermaid
3. **validator 漏检** - L1 #8 最初只检测"占位"2 字, 10 类变体是后加的

**教训**:
- **手工脚手架 > 自动化生成** (用户的偏好, "skill 必须自包含")
- **MOC 是 orphan 源** - 任何 MOC 重建都要保留 附录 + 关系图 段
- **Mermaid 中文 parens 反复出现** - 改一次不行, 修完目录就忘. 建议在 skill 里加 `.format_mermaid()` 函数.

## 关联 Skill

- `book-vault-analysis` - 生成 vault 的 skill (本 skill 是其 QA 补充)
- `literary-zh-analysis` - 包含 L1 + L2 校验器
- `` - 通用 Obsidian vault 模式