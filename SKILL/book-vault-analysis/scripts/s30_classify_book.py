"""
将图书分类到 14 大类 (T1-T14) 之一 + 小类。

用法:
    python3 s30_classify_book.py <SCRATCH_DIR>/metadata.json

返回 JSON:
    {"main": "T1", "sub": "小说", "confidence": 0.92, ...}
"""
import sys
import json
from pathlib import Path


# 14 大类关键词启发式分类 (可与 LLM 配合使用)
TYPE_KEYWORDS = {
    "T1_literary": {
        "type_name": "文学",
        "sub": "小说/散文/诗歌/纪实文学",
        "title_keywords": ["小说", "故事", "传", "情", "录", "记", "文集"],
    },
    "T2_philosophy": {
        "type_name": "思想史/哲学",
        "sub": "哲学/思想史/思想评论",
        "title_keywords": ["哲学", "思想", "智慧", "论", "沉思", "随笔", "人生"],
    },
    "T3_methodology": {
        "type_name": "方法论/自助",
        "sub": "时间管理/学习方法/习惯养成",
        "title_keywords": ["方法", "学习", "高效", "习惯", "成长", "刻意练习", "如何", "卡片"],
    },
    "T4_investment": {
        "type_name": "投资/经济",
        "sub": "价值投资/宏观/周期/经济学",
        "title_keywords": ["投资", "价值", "周期", "经济", "宏观", "资本", "证券", "基金", "文明"],
    },
    "T5_business": {
        "type_name": "商业/管理",
        "sub": "商业/创业/管理/营销",
        "title_keywords": ["商业", "创业", "管理", "营销", "原则", "纳瓦尔", "宝典"],
    },
    "T6_politics": {
        "type_name": "政经/时政",
        "sub": "政治评论/国际关系/政策分析",
        "title_keywords": ["政治", "困局", "博弈", "战略", "美国", "中国", "政经"],
    },
    "T7_history": {
        "type_name": "历史/纪实",
        "sub": "历史/传记/游记/纪实",
        "title_keywords": ["历史", "战争", "纪实", "二战", "回忆录"],
    },
    "T8_psychology": {
        "type_name": "心理/自助",
        "sub": "心理学/情绪管理/自助",
        "title_keywords": ["心理", "情绪", "压力", "焦虑", "认知", "情感", "疗愈"],
    },
    "T9_science": {
        "type_name": "科普/科学",
        "sub": "科学/自然/技术/医学",
        "title_keywords": ["科普", "科学", "自然", "技术", "物理", "化学", "生物", "天文", "费曼"],
    },
    "T10_education": {
        "type_name": "教育/学习",
        "sub": "教育/育儿/学习方法",
        "title_keywords": ["教育", "育儿", "学习", "教学", "孩子", "成长"],
    },
    "T11_art": {
        "type_name": "艺术/设计",
        "sub": "艺术/设计/建筑/摄影",
        "title_keywords": ["艺术", "设计", "建筑", "摄影", "绘画", "美学", "音乐"],
    },
    "T12_parenting": {
        "type_name": "育儿/家庭",
        "sub": "育儿/家庭/健康/养生",
        "title_keywords": ["育儿", "家庭", "健康", "养生", "亲子", "教养"],
    },
    "T13_travel": {
        "type_name": "旅行/地理",
        "sub": "旅行文学/游记/地理/文化",
        "title_keywords": ["旅行", "游记", "走遍", "去", "游", "巴黎", "地理", "文化"],
    },
    "T14_mixed": {
        "type_name": "混合 (跨大类)",
        "sub": "文学+哲学/历史+旅行/...",
        "title_keywords": [],
    },
}


def classify(title: str, author: str = "", publisher: str = "") -> dict:
    """基于书名/作者的启发式分类。LLM 可增强此函数。

    返回 confidence 字段, ≥ 0.85 表示高置信度 (自动确认), < 0.85 表示低置信度 (询问用户).
    """
    title_lower = (title or "").lower()
    scores = {}

    for type_id, info in TYPE_KEYWORDS.items():
        # T14 混合类型 - 留空, 不参与关键词匹配
        if not info["title_keywords"]:
            continue
        score = 0
        for kw in info["title_keywords"]:
            if kw in title:
                score += 1
        if score > 0:
            scores[type_id] = score

    # 默认 T1 文学 (无匹配时) - 低置信度
    if not scores:
        return {
            "main": "T1",
            "sub": "小说",
            "type_name": "文学",
            "confidence": 0.5,
            "needs_user_confirmation": True,
            "reasoning": "无强关键词匹配, 默认 T1 文学, 需用户确认",
        }

    # 最高分胜出
    best_type = max(scores, key=scores.get)
    info = TYPE_KEYWORDS[best_type]
    # 置信度计算: 1 keyword = 0.5, 2 = 0.65, 3 = 0.8, 4+ = 0.85+
    base_conf = 0.5
    keyword_conf = min(scores[best_type] * 0.15, 0.45)
    confidence = min(base_conf + keyword_conf, 0.95)

    return {
        "main": best_type,
        "sub": info.get("sub", info["type_name"]),
        "type_name": info["type_name"],
        "confidence": confidence,
        "needs_user_confirmation": confidence < 0.85,
        "reasoning": f"书名匹配 {scores[best_type]} 个关键词: {info['type_name']}",
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 s30_classify_book.py <metadata.json>")
        sys.exit(1)

    meta_path = Path(sys.argv[1])
    if not meta_path.exists():
        print(f"错误: metadata 文件不存在: {meta_path}")
        sys.exit(1)

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    result = classify(
        meta.get("title", ""),
        meta.get("creator", ""),
        meta.get("publisher", "")
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
