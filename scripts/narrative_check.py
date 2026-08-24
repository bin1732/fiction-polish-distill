#!/usr/bin/env python3
"""narrative_check.py — 叙事层质量检测（语义层重构）

检测维度（对应各平台官方判定标准："情节叙事不清、结构混乱、转折生硬、逻辑割裂"）:
    1. 起承转合结构: 开头是否直接铺陈、正文是否推进、结尾是否有钩子/余韵
    2. 逻辑链: 因果密度 vs 硬转折密度比值、事件推进是否依赖"突然"式硬跳
    3. 转折自然度: 硬转折词（突然/然而/就在这时等）密度，提示四步渐进重构
    4. 伏笔呼应: 前文出现的独特名词在后文的复现率（伏笔是否回收）
    5. 五感细节密度: 每千字感官细节数（视觉/听觉/嗅觉/触觉/味觉）
    6. 场景完整性: 时间/地点/人物/事件/情绪五要素标记覆盖

用法:
    python3 narrative_check.py <文件.md>            # 文本检测报告
    python3 narrative_check.py <文件.md> --json     # JSON 输出

说明: 全部为确定性规则检测（同文本必同结果），结果仅供作者自查参考；
      检测不到维度信息时如实标记"未检测"，不伪造结论。
"""

import json
import re
import sys
from pathlib import Path

VERSION = "1.0.5"

# ---- 内置词表（零外部依赖，纯标准库 + 内置规则） ----

HARD_TURN = [
    "突然", "忽然", "猛然", "顿时", "骤然", "就在这时", "就在此时",
    "然而", "但是", "却没想到", "谁知", "岂料", "冷不防",
    "毫无征兆", "猝不及防", "猛地", "猝然", "乍然", "陡然", "霍然", "遽然",
    "猛然间", "忽然间", "骤然间", "蓦地", "蓦然", "霎时", "倏地", "转瞬",
]
CAUSAL = [
    "因为", "所以", "因此", "于是", "由于", "导致", "使得", "从而", "以致",
    "缘故", "缘由", "起因", "归根", "源于", "出于", "鉴于", "因而", "故此",
    "是以", "为此", "据此", "据此可见", "归根结底",
]
SENSE_WORDS = {
    "视觉": [
        "看见", "看到", "望去", "泛着", "映出", "闪烁着", "映入", "远眺", "凝视", "瞥见",
        "扫视", "打量", "注视", "闪着", "透出", "浮着", "漾着", "缀着", "罩着", "笼着",
        "挂着", "铺着", "映着", "折射", "倒映", "轮廓", "光影", "斑驳", "亮着", "暗着",
        "晃眼", "刺目", "幽暗", "微光", "阴影",
    ],
    "听觉": [
        "听见", "传来", "响起", "声音", "窸窣", "轰鸣", "低语", "回荡", "脚步", "枪声",
        "风声", "雨声", "蝉鸣", "犬吠", "钟声", "啜泣", "叹息", "呢喃", "咆哮", "尖啸",
        "嗡嗡", "吱呀", "咔嚓", "扑通", "咕嘟", "簌簌", "唦唦", "回响", "嘈杂", "寂静",
    ],
    "嗅觉": [
        "气味", "闻到", "飘来", "芬芳", "腥", "香", "臭", "焦糊",
        "清香", "腐臭", "血腥", "铁锈味", "烟火气", "潮湿", "霉味", "甜腻",
        "苦涩味", "脂粉香", "草木香", "药味", "酒气", "油烟",
    ],
    "触觉": [
        "冰凉", "滚烫", "粗糙", "滑腻", "刺痛", "温热", "发麻", "僵硬", "黏腻",
        "潮湿", "冰冷", "灼热", "柔软", "生硬", "发凉", "发烫", "刺骨", "发颤",
        "紧绷", "松弛", "湿滑", "干涩", "酥麻", "生疼",
    ],
    "味觉": [
        "苦涩", "甘甜", "酸涩", "辛辣", "咸", "甜", "涩", "回味",
        "发苦", "发甜", "齁", "辣", "麻", "鲜", "腥膻", "寡淡", "甘冽", "微酸",
    ],
}
TIME_MARK = [
    "清晨", "黄昏", "夜晚", "黎明", "傍晚", "午后", "深夜", "正午", "翌日", "次日",
    "三月", "寒冬", "盛夏", "拂晓", "破晓", "薄暮", "入夜", "子时", "午时",
    "黄昏时分", "夜半", "晌午", "凌晨", "暮色", "晨曦", "余晖", "月落", "日出", "日落",
    "秋日", "春日", "隆冬", "夏夜",
]
PLACE_MARK = [
    "房间", "街道", "山谷", "森林", "宫殿", "书房", "庭院", "车厢", "码头", "天台",
    "巷子", "废墟", "桥上", "河边", "屋顶", "地窖", "密室", "长廊", "亭子", "山洞",
    "溪边", "庙宇", "城墙", "客栈", "酒馆", "集市", "田埂", "坟场", "悬崖", "渡口",
    "庭院深处", "后山", "竹林", "石桥", "渡船",
]
EMOTION_MARK = [
    "愤怒", "欣喜", "恐惧", "悲伤", "焦虑", "平静", "激动", "忐忑", "释然", "绝望",
    "期待", "懊悔", "心慌", "窃喜", "羞赧", "惊愕", "怅然", "酸楚", "亢奋", "恹恹",
    "惴惴", "惶惑", "安心", "麻木",
]
ACTION_MARK = [
    "走进", "转身", "坐下", "站起来", "握住", "推开", "拔出", "跪下", "狂奔", "后退",
    "捡起", "放下", "抬头", "低头", "攥紧", "松开", "迈步", "蹲下", "起身", "拦住",
    "让开", "扑过去", "躲开", "侧身", "抱臂", "搓手", "跺脚", "叹气", "皱眉", "咬唇",
    "闭眼", "睁眼", "摆手", "点头", "摇头", "耸肩",
    "俯身", "仰头", "别过脸", "按住", "抽出", "踢开", "攥着", "握着",
]

HARD_TURN_PAT = re.compile("|".join(re.escape(w) for w in HARD_TURN))
CAUSAL_PAT = re.compile("|".join(re.escape(w) for w in CAUSAL))
SENSE_PATS = {k: re.compile("|".join(re.escape(w) for w in v)) for k, v in SENSE_WORDS.items()}
TIME_PAT = re.compile("|".join(re.escape(w) for w in TIME_MARK))
PLACE_PAT = re.compile("|".join(re.escape(w) for w in PLACE_MARK))
EMOTION_PAT = re.compile("|".join(re.escape(w) for w in EMOTION_MARK))
ACTION_PAT = re.compile("|".join(re.escape(w) for w in ACTION_MARK))

NOUN_PAT = re.compile(r"[\u4e00-\u9fa5]{2,4}")


def split_paragraphs(text):
    """按空行/换行切分段落。"""
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    return paras


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[。！？；.!?])", text) if s.strip()]


def check_structure(text, paras):
    """1. 起承转合结构检测。"""
    issues, advices = [], []
    total_chars = len(text)
    if total_chars < 300:
        return {"status": "skip", "reason": "文本过短（<300字），不评估整体结构"}
    if len(paras) < 3:
        return {"status": "skip", "reason": "段落过少，无法评估起承转合"}
    head = "".join(paras[: max(1, len(paras) // 10)])
    tail = "".join(paras[-max(1, len(paras) // 10):])
    # 开头铺垫：开头 20% 出现场景/时间/人物铺垫标记
    open_marks = len(TIME_PAT.findall(head)) + len(PLACE_PAT.findall(head)) + len(ACTION_PAT.findall(head))
    if open_marks < 1:
        issues.append("开头缺乏场景/时间/人物铺垫标记（可能直接平铺直叙）")
        advices.append("开头 1-2 段建议交代时间/地点/人物状态，建立画面锚点")
    # 结尾钩子：结尾 20% 是否有悬念/反常识/余韵
    tail_sent = split_sentences(tail)
    hook = False
    for s in tail_sent[-3:]:
        if any(w in s for w in ("却", "但", "忽然", "没想到", "?")) or s.endswith("。"):
            hook = True
    if not hook and len(tail_sent) > 0:
        issues.append("结尾缺少钩子/余韵（章节结尾宜留悬念、反转或情绪余味）")
        advices.append("结尾末句改为：悬念式（却不知…）、反转式、或情绪留白式短句")
    return {"status": "warn" if issues else "ok", "issues": issues, "advices": advices}


def check_logic(text):
    """2. 逻辑链：因果密度 vs 硬转折密度。"""
    turns = len(HARD_TURN_PAT.findall(text))
    causals = len(CAUSAL_PAT.findall(text))
    total_chars = len(text)
    if total_chars < 100:
        return {"status": "skip", "reason": "文本过短"}
    hard_turn_rate = turns * 1000 / total_chars
    if hard_turn_rate > 6:
        return {
            "status": "warn",
            "hard_turns": turns,
            "hard_turn_rate": round(hard_turn_rate, 1),
            "issues": [f"硬转折词密度 {hard_turn_rate:.1f}/千字（阈值 ≤6），事件推进依赖'突然/然而'式硬跳"],
            "advices": ["硬转折改为四步渐进：铺垫（征兆）→ 触发（事件）→ 反应（人物）→ 余波（影响）"],
        }
    if causals == 0 and turns >= 2:
        return {
            "status": "warn",
            "hard_turns": turns,
            "issues": ["有硬转折但无因果衔接词，事件链可能断裂"],
            "advices": ["转折前补 1 句因果铺垫（为何发生），再触发事件"],
        }
    return {"status": "ok", "hard_turns": turns, "causal_links": causals}


def check_turn_natural(text):
    """3. 转折自然度：定位硬转折词所在句子，标注重构建议。"""
    hits = []
    for s in split_sentences(text):
        m = HARD_TURN_PAT.search(s)
        if m and len(s) <= 120:
            hits.append({"sentence": s[:60], "word": m.group(0), "line": _line_of(text, s)})
    if len(hits) > 6:
        return {"status": "warn", "count": len(hits), "sample": hits[:6],
                "advices": ["连续硬转折过多，先交代'为什么'再触发事件（铺垫→触发→反应→余波）"]}
    return {"status": "ok", "count": len(hits), "sample": hits[:3]}


def check_foreshadow(text, paras):
    """4. 伏笔呼应：前文独特名词在后文复现率。"""
    if len(paras) < 8:
        return {"status": "skip", "reason": "段落过少（<8），无法评估伏笔呼应"}
    half = len(paras) // 2
    head = "".join(paras[:half])
    tail = "".join(paras[half:])
    head_nouns = set()
    for m in NOUN_PAT.finditer(head):
        w = m.group(0)
        if head.count(w) == 1 and w not in HARD_TURN and w not in CAUSAL:
            head_nouns.add(w)
    unique = [w for w in head_nouns if len(head_nouns) > 0][:30]
    if not unique:
        return {"status": "ok", "reason": "无显著独特名词"}
    recalled = [w for w in unique if w in tail]
    rate = len(recalled) / len(unique)
    if rate < 0.15 and len(unique) >= 8:
        return {
            "status": "warn",
            "unique_nouns": len(unique),
            "recall_rate": round(rate, 2),
            "advices": ["前文独特名词（可能为伏笔）后文复现率低，建议检查未回收的伏笔"],
        }
    return {"status": "ok", "unique_nouns": len(unique), "recall_rate": round(rate, 2)}


def check_sense_density(text):
    """5. 五感细节密度。"""
    if len(text) < 200:
        return {"status": "skip", "reason": "文本过短"}
    total_chars = len(text)
    counts = {k: len(p.findall(text)) for k, p in SENSE_PATS.items()}
    total = sum(counts.values())
    rate = total * 1000 / total_chars
    if total == 0:
        return {"status": "warn", "rate": 0,
                "issues": ["无任何感官细节（每千字 0 处）——典型 AI 文特征：画面感缺失"],
                "advices": ["每个场景注入 ≥2 种感官（视觉+听觉为主），且与人物视角绑定（'他闻到…'而非'空气中弥漫…'）"]}
    if rate < 2:
        return {"status": "warn", "rate": round(rate, 1), "counts": counts,
                "issues": [f"感官密度 {rate:.1f}/千字（建议 ≥2）"],
                "advices": ["补 1-2 处具体感官细节（嗅觉/触觉最易增强真实感）"]}
    return {"status": "ok", "rate": round(rate, 1), "counts": counts}


def check_scene_complete(text):
    """6. 场景完整性：五要素标记覆盖。"""
    total_chars = len(text)
    if total_chars < 200:
        return {"status": "skip", "reason": "文本过短"}
    marks = {
        "时间": len(TIME_PAT.findall(text)),
        "地点": len(PLACE_PAT.findall(text)),
        "人物行动": len(ACTION_PAT.findall(text)),
        "情绪": len(EMOTION_PAT.findall(text)),
    }
    missing = [k for k, v in marks.items() if v == 0]
    if len(missing) >= 2:
        return {"status": "warn", "marks": marks, "missing": missing,
                "advices": ["场景宜交代时间/地点/人物行动/情绪四要素，当前缺失: " + "/".join(missing)]}
    return {"status": "ok", "marks": marks}


def _line_of(text, snippet):
    """定位片段所在行号（1-based）。"""
    idx = text.find(snippet[:20])
    if idx < 0:
        return 0
    return text.count("\n", 0, idx) + 1


def run_check(text):
    paras = split_paragraphs(text)
    return {
        "structure": check_structure(text, paras),
        "logic": check_logic(text),
        "turn_natural": check_turn_natural(text),
        "foreshadow": check_foreshadow(text, paras),
        "sense_density": check_sense_density(text),
        "scene_complete": check_scene_complete(text),
    }


def report(results, as_json=False):
    labels = {"ok": "✅ 通过", "warn": "⚠ 建议处理", "skip": "— 跳过"}
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    print("══ 叙事层质量检测报告（语义层）══")
    names = {
        "structure": "1. 起承转合结构",
        "logic": "2. 逻辑链（因果 vs 硬转折）",
        "turn_natural": "3. 转折自然度",
        "foreshadow": "4. 伏笔呼应",
        "sense_density": "5. 五感细节密度",
        "scene_complete": "6. 场景完整性",
    }
    warn_count = 0
    for key, label in names.items():
        r = results[key]
        status = r.get("status")
        if status == "warn":
            warn_count += 1
        print(f"\n{labels.get(status, status)} {label}")
        if status == "skip":
            print(f"   {r.get('reason', '')}")
            continue
        for k, v in r.items():
            if k in ("status", "issues", "advices", "sample", "missing", "counts", "marks"):
                continue
            if isinstance(v, (int, float)):
                print(f"   {k}: {v}")
        for i in r.get("issues", []):
            print(f"   ⚠ {i}")
        for a in r.get("advices", []):
            print(f"   💡 {a}")
        for s in r.get("sample", [])[:3]:
            ln = s.get("line", 0)
            print(f"   · L{ln} [{s.get('word', '')}] {s.get('sentence', '')}")
    print(f"\n结论: {'⚠ 建议按提示处理' if warn_count else '✅ 叙事层检测通过'}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    as_json = "--json" in argv
    path = argv[0]
    p = Path(path)
    if not p.exists():
        print(f"文件不存在: {path}")
        return 1
    text = p.read_text(encoding="utf-8", errors="replace")
    results = run_check(text)
    report(results, as_json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
