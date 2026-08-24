#!/usr/bin/env python3
"""quality_check.py — 小说润色蒸馏专家 1.0.5 质量检测

用法:
    python3 quality_check.py <文件.md>                  # 检测单章
    python3 quality_check.py <文件.md> --json           # JSON格式输出
    python3 quality_check.py <文件.md> --original 原稿.md   # 对照原稿计算信息/术语保留度
    python3 quality_check.py <文件.md> --human 4 --senses 3  # 显式传入人味技法/五感注入数(由处理方统计)

检查项:
    1. 句长变异系数(CV>0.5)        2. 连续12字相同序列(=0)
    3. 连接词密度(≤2/300字)       4. 前100字切入(无概括性铺垫)
    5. 信息保留度(需--original)    6. 术语保留度(需--original)
    7. 情感标签(<3处)              8. 结尾方式(反常识短句/反问)
    9. 对话占比(30-50%)           10. 日韩语体检查(仅日韩文本)
    11. 反AI评分(0-100)           12. 内容安全前置过滤(红线拒绝)

数据源: 连接词/情感标签/比喻词表统一从 references/antiai_blacklist.json 加载(单一数据源)。
说明: 信息保留度/术语保留度需要前后对照, 未提供 --original 时如实标记"未检测"而非伪造 100%。
"""

import re
import sys
import json
import math
from pathlib import Path

BLACKLIST_FILE = Path(__file__).parent.parent / "references" / "antiai_blacklist.json"

# 内容安全红线关键词表（与 references/content-safety.md 四类红线对应）。
# 关键词匹配存在局限，命中后仍需上层 agent 结合语义复核；列表可按需扩展。
RED_LINE_KEYWORDS = {
    "涉政": ["分裂国家", "颠覆国家政权", "台独", "港独", "疆独", "藏独", "推翻政权", "领土分裂", "民族仇恨煽动", "宗教极端"],
    "涉黄": ["儿童色情", "幼女性行为", "恋童", "未成年人性行为", "色情交易", "卖淫", "嫖娼", "性服务交易",
             "性交", "做爱", "口交", "性行为描写"],
    "涉暴": ["制作炸弹", "制作炸药", "制造爆炸物", "教唆自杀", "鼓励自杀", "自杀方法", "杀人教程", "恐怖袭击策划", "暴力犯罪教学"],
    "不良引导": ["赌博技巧教学", "制毒方法", "制作毒品", "诈骗话术教程", "编写木马教程", "制作病毒教程", "网络攻击教程",
             "批量洗稿", "伪原创工具", "AI批量生成发布", "绕过内容审核", "规避平台检测", "自动化发文教程",
             "洗稿教程", "抄袭转换工具", "批量抄袭", "内容农场教程"],
}

# 黑名单 JSON 中 category 字段随语言不同，这里给出规范类别的跨语言别名映射。
CATEGORY_ALIASES = {
    "逻辑连接词": ["逻辑连接词", "logical_connectors", "接続詞", "접속사"],
    "情感标签": ["情感标签", "emotional_labels", "感情直球", "감정직구"],
    "过度比喻": ["过度比喻", "excessive_metaphor", "過剰比喩", "과도비유"],
    "AI句式模板": ["AI句式模板", "sentence_templates", "AI句式テンプレート", "AI문장템플릿"],
    "提示词残留": ["提示词残留", "prompt_residue", "プロンプト残骸", "프롬프트잔여"],
    "情感直球": ["情感直球", "emotional_labels", "感情直球", "감정직구"],
}


def get_category_pattern(groups, canonical):
    """按规范类别名跨语言合并 pattern（中/英/日/韩别名全查）。"""
    parts = []
    for alias in CATEGORY_ALIASES.get(canonical, [canonical]):
        if alias in groups and groups[alias]:
            parts.append(groups[alias])
    return "|".join(parts)


def load_blacklist():
    """从黑名单 JSON 加载规则（单一数据源，脚本不再维护第二份词表）。"""
    if not BLACKLIST_FILE.exists():
        print(f"❌ 黑名单文件不存在: {BLACKLIST_FILE}")
        print("  请确认 skill 目录结构完整（需要 references/antiai_blacklist.json）")
        sys.exit(2)
    try:
        return json.loads(BLACKLIST_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"❌ 黑名单 JSON 解析失败: {e}")
        sys.exit(2)


def rules_by_language(blacklist, lang):
    """取某语言的规则，按 category 分组，每组 pattern 用 | 合并为单一正则。"""
    groups = {}
    for r in blacklist.get("rules", []):
        if r.get("language") != lang:
            continue
        cat = r.get("category", "未分类")
        groups.setdefault(cat, []).append(r["pattern"])
    return {cat: "|".join(patterns) for cat, patterns in groups.items()}


def detect_language(text):
    """四语检测；检测失败回退英文（与 SKILL.md 8.3 一致）。"""
    ko_chars = len(re.findall(r"[\uAC00-\uD7AF\u1100-\u11FF]", text))
    cjk_chars = len(re.findall(r"[\u4E00-\u9FFF]", text))
    en_chars = len(re.findall(r"[a-zA-Z]", text))
    ja_kana = len(re.findall(r"[\u3040-\u309F\u30A0-\u30FF]", text))

    if ko_chars > len(text) * 0.15:
        return "ko"
    if ja_kana > len(text) * 0.1:
        return "ja"
    if en_chars > cjk_chars:
        return "en"
    # 中文字符占多数 -> zh
    if cjk_chars > 0:
        return "zh"
    # 其他/混合 -> 英文回退
    return "en"


SENTENCE_SPLIT = {
    "zh": r"[。！？!?；;]+",
    "en": r"[.!?]+",
    "ja": r"[。！？!?]+",
    "ko": r"[.!?。！？]+",
}


def split_sentences(text, lang):
    """按语言标点切句，返回去空句列表。

    英文模式先保护常见缩写（Mr./Dr./e.g./U.S. 等），避免缩写句点被误切。
    """
    if lang == "en":
        # 保护常见缩写：把 "Mr." 临时替换为 "Mr\u0000"，切句后再还原
        abbr = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr|e\.g|i\.e|etc|vs|U\.S|U\.K|A\.M|P\.M)\.", re.IGNORECASE)
        protected = []
        def _keep(m):
            protected.append(m.group(0))
            return f"\u0000{len(protected) - 1}\u0000"
        text2 = abbr.sub(_keep, text)
        parts = [s.strip() for s in re.split(r"[.!?]+", text2) if s.strip()]
        out = []
        for p in parts:
            p = re.sub(r"\u0000(\d+)\u0000", lambda m: protected[int(m.group(1))], p)
            out.append(p)
        return out
    parts = [s.strip() for s in re.split(SENTENCE_SPLIT.get(lang, r"[.!?。！？]+"), text)]
    return [p for p in parts if p]


def check_sentence_cv(text, lang):
    """句长变异系数 CV = 句长标准差 / 平均句长。真实按句切分计算。"""
    sents = split_sentences(text, lang)
    if len(sents) < 2:
        return 0.0, len(sents)
    lens = [len(s) for s in sents]
    avg = sum(lens) / len(lens)
    if avg == 0:
        return 0.0, len(sents)
    var = sum((l - avg) ** 2 for l in lens) / len(lens)
    return math.sqrt(var) / avg, len(sents)


def check_12char_repeat(text):
    """连续12字相同序列检测：滑动窗口查重复。返回重复序列列表。"""
    found = set()
    seen = {}
    n = len(text)
    for i in range(n - 11):
        seg = text[i:i + 12]
        if seg in seen:
            found.add(seg)
        else:
            seen[seg] = i
    return sorted(found)


def check_opening(text):
    """前100字切入：是否以概括性铺垫开头（模板化开头词命中即判失败）。

    词表直接取自黑名单 JSON 的模板化开头类（zh-004/en-004/ja-005/ko-005），
    运行时从唯一数据源加载，不硬编码第二份；"随着"单独不判（会误杀正常写作），
    仅匹配黑名单中的完整模板"随着.*的发展"。
    """
    opening = text[:100]
    # 从黑名单 JSON 加载模板化开头类词表（单一数据源）
    try:
        blacklist = json.loads(BLACKLIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        blacklist = {}
    template_pats = []
    for r in blacklist.get("rules", []):
        if r.get("category") in ("模板化开头", "template_openings", "導入テンプレート", "도입템플릿"):
            for part in r.get("pattern", "").split("|"):
                part = part.strip()
                if part:
                    template_pats.append(part)
    if not template_pats:
        # 兜底（黑名单缺失时）：与已发布的模板化开头类保持一致
        template_pats = [
            "在当今", "众所周知", "总而言之", "近年来",
            "in today's world", "in modern society", "as we all know", "nowadays",
            "今の時代", "現代社会", "周知のとおり",
            "요즘", "현대사회", "다들 알다시피",
        ]
    # 黑名单 pattern 是正则（如 zh-004 的"在当今.*时代"），直接编译为正则匹配；
    # 不 re.escape（escape 会把 .* 的 . 转义成 \. 导致模板失配）。
    hits = []
    for p in template_pats:
        try:
            if re.search(p, opening):
                hits.append(p)
        except re.error:
            # 兜底：非法正则退化为字面子串匹配
            if p in opening:
                hits.append(p)
    return len(hits) == 0, hits


def check_ending(text):
    """结尾方式：最后一句为短句（≤15字/词）或含反问/省略号。

    修正：仅"短句"不判为反常识（避免"他走了。"等平庸短句通过），
    需短句 + 意外/转折信号（否定/转折/意外词），或反问/省略号。
    """
    tail = text[-120:]
    # split 保留标点（捕获组），否则句尾"？/！/…"会被切掉导致反问检测失效
    parts = re.split(r"([。！？!?…]+)", tail)
    sents = []
    for i in range(0, len(parts) - 1, 2):
        seg = parts[i].strip()
        if seg:
            sents.append(seg + parts[i + 1])
    if parts and parts[-1].strip():
        sents.append(parts[-1].strip())
    sents = [s for s in sents if s]
    if not sents:
        return False, "无有效结尾句"
    last = sents[-1]
    if re.search(r"[？?]|…+|[.!?]{2,}", last):
        return True, f"反问/省略收尾: {last[:30]}"
    # 意外/转折信号词：否定、转折、意外（用双字以上组合，避免单字"但/可/再"误判普通短句）
    surprise = re.compile(r"没有|没人|谁也|竟然|居然|却|不过|反而|只是|不是…而是|只有…才|再也没有", )
    if len(last) <= 15 and surprise.search(last):
        return True, f"反常识短句收尾: {last}"
    return False, f"结尾句偏长或平淡: {last[:30]}"


def check_dialogue_ratio(text, lang):
    """对话占比：引号内容占全文比例。

    中文/英文标准 30-50%；日韩文本**只设下限 30%**（上限不判失败——
    日韩网文/轻小说对话密集是题材常态，日常系"对话占60%以上"为创作特征，
    无法用固定上限区分"正常密集"与"过度"，因此仅对对话不足给出提示）。
    无对话文本不判失败（不适用）。

    修正：支持英文单引号对话（'...'）；撇号（it's/don't）因无闭合引号不误判。
    """
    dialogs = re.findall(r"「[^」]*」|\"[^\"]*\"|『[^』]*』|'[^']*'", text)
    dp = round(sum(len(d) for d in dialogs) / len(text) * 100, 1) if text else 0
    if dp == 0:
        return True, dp  # 文本不含对话，检查不适用，不判失败
    if lang in ("ja", "ko"):
        return dp >= 30, dp  # 日韩：仅下限，对话密集不判失败
    return 30 <= dp <= 50, dp


def check_japanese(text):
    """日文语体检测：です/ます vs だ/である 密度 + AI接续词 + 中断记号。"""
    result = {}
    desu_masu = len(re.findall(r"です|ます", text))
    da_dearu = len(re.findall(r"だ|である", text))
    total = desu_masu + da_dearu
    result["です/ます密度"] = round(desu_masu / total * 100, 1) if total else 0
    result["だ/である密度"] = round(da_dearu / total * 100, 1) if total else 0
    result["AI接続詞"] = len(re.findall(r"まず|次に|最後に|要するに|したがって|それゆえ", text))
    result["中断記号"] = len(re.findall(r"──|……", text))
    return result


def check_korean(text):
    """韩文语体检测：다/요/하십시오 密度 + AI接续词。

    修正：-합니다 / -습니다 的 다 归入敬语（하십시오）密度，不重复计入平叙 다 密度。
    """
    result = {}
    hasipsio = len(re.findall(r"하십시오|합니다|습니다", text))
    # 平叙 다：排除敬语终结（합니다/습니다）里的 다，只计独立平叙句尾
    da_end = len(re.findall(r"(?<!니)다(?![가-힣])", text))
    yo_end = len(re.findall(r"요(?![가-힣])", text))
    total = da_end + yo_end + hasipsio
    result["다密度"] = round(da_end / total * 100, 1) if total else 0
    result["요密度"] = round(yo_end / total * 100, 1) if total else 0
    result["하십시오密度"] = round(hasipsio / total * 100, 1) if total else 0
    result["AI접속사"] = len(re.findall(r"먼저|다음으로|마지막으로|요컨대|따라서|그러므로", text))
    return result


def safety_scan(text):
    """内容安全前置过滤：四类红线关键词扫描。命中输出类型与位置。"""
    hits = []
    for category, words in RED_LINE_KEYWORDS.items():
        for w in words:
            for m in re.finditer(re.escape(w), text):
                pos = text.count("\n", 0, m.start()) + 1
                hits.append({"category": category, "keyword": w, "line": pos})
    return hits


# ---- AI 痕迹残留词表（对应各平台"AI 铁证"案例：未删除的对话痕迹/格式残留） ----
# 硬残留：AI 对话/提示词痕迹（如"以下是为您修改、润色和优化后的内容"——已有章节因此被平台锁定）
RESIDUE_HARD = [
    "以下是为您修改、润色和优化后的内容",
    "以下是为您生成的", "以下是修改后的", "以下是润色后的", "以下是我的建议",
    "这是为您修改后的", "好的，这是", "当然可以", "希望对您有帮助", "如果您需要进一步",
    "这是一个很好的问题", "作为AI", "作为人工智能", "我无法完成", "对不起，我不能", "我不能提供",
    "As an AI", "Here is the", "Sure, here", "Certainly", "I'm sorry, but I cannot",
    "修改后的版本如下", "优化后的内容如下", "重新生成了", "已为您", "请查收", "供您参考",
    "您也可以", "如需", "如果还有", "还有什么可以", "随时告诉我", "有任何问题",
    "不要犹豫", "祝您一切顺利", "希望您能", "如您所愿", "明白了", "收到", "开始吧",
    "让我们一起来", "让我为您", "在接下来的内容中", "首先让我", "我将为您",
]
# 软残留：Markdown 格式痕迹（正文中不应出现）
RESIDUE_SOFT = ["**", "##", "```", "---", "| ", "# ", "* ", "> ", "1. ", "- ", "["]
# 软残留：AI 对称句式模板（软特征）
SYMMETRIC_PAT = re.compile(
    r"(一方面[^。]{2,20}另一方面|不但[^。]{2,20}而且|不仅[^。]{2,20}还|"
    r"无论[^。]{2,20}都|总而言之|综上所述|需要注意的是|众所周知|在当今|近年来)"
)


def residue_scan(text):
    """AI 痕迹残留扫描：提示词/指令残留（硬，铁证级）+ Markdown/对称模板（软，疑似级）。"""
    hits = []
    for w in RESIDUE_HARD:
        for m in re.finditer(re.escape(w), text, re.IGNORECASE):
            hits.append({"type": "hard", "pattern": w[:20], "line": text.count("\n", 0, m.start()) + 1})
    for w in RESIDUE_SOFT:
        for m in re.finditer(re.escape(w), text):
            hits.append({"type": "soft_format", "pattern": w, "line": text.count("\n", 0, m.start()) + 1})
    for m in SYMMETRIC_PAT.finditer(text):
        hits.append({"type": "soft_template", "pattern": m.group(0)[:20], "line": text.count("\n", 0, m.start()) + 1})
    # 同位置同类型去重
    seen, uniq = set(), []
    for h in hits:
        key = (h["type"], h["line"], h["pattern"])
        if key not in seen:
            seen.add(key)
            uniq.append(h)
    return uniq


# ---- P1-1 统计层特征（对应检测原理：困惑度/突发性/词汇多样性/熵） ----
# AI 高频套话词（低困惑度文本的典型成分）
AI_COMMON_WORDS = [
    "首先", "其次", "最后", "总而言之", "综上所述", "需要注意的是", "与此同时", "此外",
    "以及", "并且", "因此", "所以", "但是", "然而", "其实", "实际上", "基本上",
    "确实", "一定", "非常", "十分", "值得注意的是", "从这个角度", "总体来看", "不难发现",
    "换句话说", "也就是说", "值得一提的是", "更重要的是", "除此之外", "归根结底", "说到底",
    "不可否认", "诚然", "据统计", "数据显示", "高达", "多达", "将近", "至关重要", "不可或缺",
    "重中之重", "这说明了", "由此可见", "从这一点来看", "内心世界", "灵魂深处", "内心深处",
    "莫名的", "总体而言", "整体来看", "一言以蔽之", "众所周知", "在当今", "近年来",
    "毋庸置疑", "毫无疑问", "不得不承认", "需要指出的是", "一方面", "另一方面", "不仅",
    "而且", "无论", "即便", "纵然", "哪怕", "正因为如此", "推而广之",
]


def perplexity_estimate(text):
    """困惑度估算（0-100，低=疑似 AI）。

    组合指标：AI 高频套话词密度 + 字符 3-gram 重复度。
    套话词越密集、字符序列越可预测 → 得分越低（AI 文本的典型特征）。
    纯标准库实现，确定性结果。
    """
    if len(text) < 100:
        return None
    grams = {}
    for i in range(len(text) - 2):
        g = text[i:i + 3]
        grams[g] = grams.get(g, 0) + 1
    total = len(text) - 2
    # 3-gram 重复度：高频 trigram 占比（可预测性）
    top_share = 0.0
    if grams:
        top = sum(sorted(grams.values(), reverse=True)[:10])
        top_share = top / total
    # 套话词密度（每千字）
    ai_density = sum(text.count(w) for w in AI_COMMON_WORDS) * 1000 / len(text)
    # 映射到 0-100（参数经典型 AI/人类文本差异校准）
    score = 100 - min(40, ai_density * 3) - min(30, top_share * 100)
    return round(max(0, min(100, score)), 1)


def burstiness_score(text):
    """突发性（0-100，低=AI 句长平稳）。

    句长变异系数（CV）与短长交替频率的组合；人类写作句长长短交错（高突发），
    AI 写作句长均匀（低突发）。
    """
    sents = [s.strip() for s in re.split(r"(?<=[。！？；.!?])", text) if len(s.strip()) >= 4]
    if len(sents) < 6:
        return None
    lens = [len(s) for s in sents]
    mean = sum(lens) / len(lens)
    if mean == 0:
        return None
    var = math.sqrt(sum((l - mean) ** 2 for l in lens) / len(lens)) / mean
    # 短长交替次数（相邻句长度方向变化）
    alt = 0
    for i in range(1, len(lens)):
        if (lens[i] - lens[i - 1]) * (lens[i - 1] - lens[i - 2]) < 0:
            alt += 1
    alt_rate = alt / (len(lens) - 2) if len(lens) > 2 else 0
    score = min(60, var * 60) + min(40, alt_rate * 100)
    return round(max(0, min(100, score)), 1)


def lexical_diversity(text):
    """词汇多样性 TTR（0-100，低=词汇贫乏）。

    按字 2-gram 词块去重统计 type-token ratio，映射到 0-100。
    """
    if len(text) < 100:
        return None
    tokens = [text[i:i + 2] for i in range(len(text) - 1)]
    ttr = len(set(tokens)) / len(tokens) if tokens else 0
    return round(max(0, min(100, ttr * 120)), 1)


def text_entropy(text):
    """信息熵（0-100，低=分布规律）。

    字符分布香农熵；AI 文本字符分布更均匀但重复结构多（熵偏低），
    人类文本含更多非常用字（熵偏高）。
    """
    if len(text) < 100:
        return None
    from collections import Counter
    cnt = Counter(text)
    total = len(text)
    ent = 0.0
    for c, n in cnt.items():
        p = n / total
        if p > 0:
            ent -= p * math.log2(p)
    # 中文文本熵通常在 4-8 之间，映射到 0-100
    return round(max(0, min(100, (ent - 2) * 18)), 1)


def calc_anti_ai_score(text, lang, groups, sent_cv, sent_count, ja_checks=None,
                       ko_checks=None, human=0, senses=0):
    """反AI评分（0-100）。公式与 agents/de-ai-engineer.md 完全统一。

    扣分: 连接词密度×5(上限25) + 情感标签×8(上限24) + 比喻×3(上限15)
         + 句长CV<0.5扣10 / CV<0.3扣20 + 日韩接续词>2处扣10
    加分: 人味技法×3(上限15) + 五感×2(上限10)  —— 由处理方经 --human/--senses 显式传入
    """
    score = 100
    total = len(text)

    def count_hits(pattern):
        try:
            return len(re.findall(pattern, text, re.IGNORECASE)) if pattern else 0
        except re.error:
            return 0

    # 跨语言类别别名：中/英/日/韩的连接词、情感标签、比喻词表全查
    conj_c = count_hits(get_category_pattern(groups, "逻辑连接词"))
    emo_c = count_hits(get_category_pattern(groups, "情感标签"))
    biyu_c = count_hits(get_category_pattern(groups, "过度比喻"))

    density = conj_c * 300 / total if total else 0
    score -= min(int(density * 5), 25)
    score -= min(emo_c * 8, 24)
    score -= min(biyu_c * 3, 15)

    if sent_count >= 2:
        if sent_cv < 0.3:
            score -= 20
        elif sent_cv < 0.5:
            score -= 10

    if lang == "ja" and ja_checks and ja_checks.get("AI接続詞", 0) > 2:
        score -= 10
    if lang == "ko" and ko_checks and ko_checks.get("AI접속사", 0) > 2:
        score -= 10

    score += min(int(human) * 3, 15)
    score += min(int(senses) * 2, 10)

    return max(0, min(100, score))


def compute_retention(original_text, new_text, locked_terms=None):
    """信息保留度/术语保留度：与 --original 对照计算。

    信息保留度 = 原稿信息单元（单个汉字 + 字母数字串）在改稿中出现的比例。
    术语保留度 = 锁定术语在改稿中全部出现的比例。
    采用字符/词单元集合，避免整段 CJK token 因个别字改动而整体失配（曾导致 0% 假阴性）。
    """
    if not original_text:
        return None, None

    def info_units(s):
        # 单个汉字作为一个信息单元；字母/数字连续串作为一个单元
        return set(re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9]+", s))

    orig_units = info_units(original_text)
    new_units = info_units(new_text)
    if not orig_units:
        return None, None
    retained = orig_units & new_units
    info_retention = round(len(retained) / len(orig_units) * 100, 1)

    term_retention = None
    if locked_terms:
        kept = [t for t in locked_terms if t in new_text]
        term_retention = round(len(kept) / len(locked_terms) * 100, 1) if locked_terms else None
    return info_retention, term_retention


def parse_args(argv):
    """参数解析：位置参数为文件路径；--json/--original/--human/--senses 顺序无关。

    修正：--human/--senses 非法数值时明确报错退出，不再抛未捕获 ValueError。
    """
    filepath = None
    output_json = False
    original_path = None
    human = 0
    senses = 0
    locked = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--json":
            output_json = True
        elif a == "--original" and i + 1 < len(argv):
            original_path = argv[i + 1]
            i += 1
        elif a == "--human" and i + 1 < len(argv):
            try:
                human = int(argv[i + 1])
            except ValueError:
                print(f"❌ --human 参数必须是整数: {argv[i + 1]}")
                sys.exit(1)
            i += 1
        elif a == "--senses" and i + 1 < len(argv):
            try:
                senses = int(argv[i + 1])
            except ValueError:
                print(f"❌ --senses 参数必须是整数: {argv[i + 1]}")
                sys.exit(1)
            i += 1
        elif a == "--lock" and i + 1 < len(argv):
            locked = argv[i + 1].split(",")
            i += 1
        elif a.startswith("-"):
            pass  # 忽略未知选项
        else:
            if filepath is None:
                filepath = a
            else:
                original_path = a  # 第二个位置参数视为原稿
        i += 1
    return filepath, output_json, original_path, human, senses, locked


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        sys.exit(1)

    filepath, output_json, original_path, human, senses, locked = parse_args(argv)
    if not filepath:
        print("❌ 缺少文件路径参数")
        print(__doc__)
        sys.exit(1)

    try:
        text = Path(filepath).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        sys.exit(1)

    if not text.strip():
        print("❌ 空文件")
        sys.exit(1)

    blacklist = load_blacklist()
    lang = detect_language(text)
    groups = rules_by_language(blacklist, lang)

    result = {"file": filepath, "version": "1.0.5", "pass": True, "checks": {}, "issues": []}
    result["checks"]["语言"] = lang

    # ---- 0. 内容安全前置过滤（红线拒绝） ----
    red_hits = safety_scan(text)
    if red_hits:
        result["safety"] = {"pass": False, "hits": red_hits}
        result["pass"] = False
        result["issues"].append(f"内容安全未通过: {len(red_hits)}处红线命中")
        for h in red_hits[:5]:
            result["issues"].append(f"  [{h['category']}] 第{h['line']}行: {h['keyword']}")
        if output_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"⛔ 内容安全检测未通过: {filepath}")
            for h in red_hits:
                print(f"  ⛔ [{h['category']}] 第{h['line']}行: {h['keyword']}")
        sys.exit(3)  # 3 = 安全拦截

    result["safety"] = {"pass": True, "hits": []}

    total = len(text)

    # ---- 0.5 字数/长度边界（SKILL.md 8.1/8.2） ----
    # <50字：直接返回原文（SKILL 8.1）；>50000字：建议分段处理（SKILL 8.2）
    # 长度仅为提示，不判 FAIL（长度非质量缺陷）
    if total < 50:
        result["checks"]["字数"] = {"value": f"{total}字", "pass": None, "note": "输入过短(<50字)，直接返回原文"}
        if output_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"📖 质量检测 v1.0.5: {filepath}")
            print(f"  ℹ️  字数: {total}字 — 输入过短(<50字)，建议提供更多文本，直接返回原文")
        return  # 短文本不做完整检测
    if total > 50000:
        wc_note = "超过50000字，建议分段处理（每段3000-5000字效果最佳）"
    elif total > 5000:
        wc_note = "文本较长，建议分段检测（每段3000-5000字效果最佳）"
    elif total < 2000:
        wc_note = "短文本，结果仅供参考"
    else:
        wc_note = "符合标准检测区间"
    result["checks"]["字数"] = {"value": f"{total}字", "pass": None, "note": wc_note}

    # ---- 1. 句长变异系数 ----
    sent_cv, sent_count = check_sentence_cv(text, lang)
    cv_pass = sent_cv >= 0.5
    result["checks"]["句长CV"] = {"value": round(sent_cv, 2), "pass": cv_pass, "句子数": sent_count}
    if not cv_pass and sent_count >= 2:
        result["issues"].append(f"句长CV={sent_cv:.2f}<0.5，句式偏均匀")

    # ---- 2. 连续12字相同序列 ----
    repeats = check_12char_repeat(text)
    result["checks"]["12字重复"] = {"value": len(repeats), "pass": len(repeats) == 0}
    if repeats:
        result["issues"].append(f"存在{len(repeats)}处12字连续重复: {repeats[:2]}")

    # ---- 3. 连接词密度（跨语言类别别名） ----
    conj = get_category_pattern(groups, "逻辑连接词")
    if lang == "en":
        conj_c = len(re.findall(conj, text, re.IGNORECASE)) if conj else 0
    else:
        conj_c = len(re.findall(conj, text)) if conj else 0
    density = round(conj_c * 300 / total, 2) if total else 0
    conj_pass = density <= 2
    result["checks"]["连接词密度"] = {"value": f"{density}/300字", "pass": conj_pass}
    if not conj_pass:
        result["issues"].append(f"连接词过密: {density}/300字")

    # ---- 4. 前100字切入 ----
    opening_ok, opening_hits = check_opening(text)
    result["checks"]["前100字切入"] = {"value": "具体切入" if opening_ok else f"概括铺垫: {opening_hits}", "pass": opening_ok}
    if not opening_ok:
        result["issues"].append("开头有概括性铺垫，建议从具体细节切入")

    # ---- 5/6. 信息/术语保留度（需 --original 对照） ----
    original_text = None
    if original_path:
        try:
            original_text = Path(original_path).read_text(encoding="utf-8")
        except Exception as e:
            result["issues"].append(f"原稿读取失败: {e}")
    info_ret, term_ret = compute_retention(original_text, text, locked)
    if info_ret is None:
        result["checks"]["信息保留度"] = {"value": "未检测(需--original对照)", "pass": None}
    else:
        result["checks"]["信息保留度"] = {"value": f"{info_ret:g}%", "pass": info_ret >= 95}
        if info_ret < 95:
            result["issues"].append(f"信息保留度{info_ret:g}%<95%，疑似删改过多")
    if term_ret is None:
        result["checks"]["术语保留度"] = {"value": "未检测(需--original/--lock)", "pass": None}
    else:
        result["checks"]["术语保留度"] = {"value": f"{term_ret:g}%", "pass": term_ret == 100}
        if term_ret < 100:
            result["issues"].append(f"术语保留度{term_ret:g}%，锁定术语被改动")

    # ---- 7. 情感标签（跨语言类别别名，与反AI评分口径一致） ----
    emo = get_category_pattern(groups, "情感标签")
    ec = len(re.findall(emo, text, re.IGNORECASE)) if emo else 0
    e_pass = ec < 3
    result["checks"]["情感标签"] = {"value": f"{ec}次", "pass": e_pass}
    if not e_pass:
        result["issues"].append(f"情感标签过多({ec}次)，建议用身体反应替代")

    # ---- 8. 结尾方式 ----
    ending_ok, ending_note = check_ending(text)
    result["checks"]["结尾方式"] = {"value": ending_note, "pass": ending_ok}
    if not ending_ok:
        result["issues"].append("结尾平庸，建议改为反常识短句或反问")

    # ---- 9. 对话占比 ----
    d_ok, dp = check_dialogue_ratio(text, lang)
    result["checks"]["对话占比"] = {"value": f"{dp}%", "pass": d_ok}
    if not d_ok:
        result["issues"].append(f"对话占比{dp}%不在区间（中英30-50%/日韩≥30%）")

    # ---- 10. 日韩语体 ----
    ja_checks = ko_checks = None
    if lang == "ja":
        ja_checks = check_japanese(text)
        result["checks"]["日文检测"] = ja_checks
        if ja_checks["AI接続詞"] > 2:
            result["issues"].append(f"日文AI接続詞过多({ja_checks['AI接続詞']}次)")
    if lang == "ko":
        ko_checks = check_korean(text)
        result["checks"]["韩文检测"] = ko_checks
        if ko_checks["AI접속사"] > 2:
            result["issues"].append(f"韩文AI접속사过多({ko_checks['AI접속사']}次)")

    # ---- 11. 反AI评分 ----
    anti_ai = calc_anti_ai_score(text, lang, groups, sent_cv, sent_count, ja_checks, ko_checks, human, senses)
    result["checks"]["反AI评分"] = {"value": f"{anti_ai}/100", "pass": anti_ai >= 80}
    if anti_ai < 80:
        if anti_ai < 70:
            result["issues"].append(f"反AI评分{anti_ai}<70，需重新处理")
        else:
            result["issues"].append(f"反AI评分{anti_ai}在70-79区间，建议二次处理")

    # ---- 12. AI 痕迹残留（提示词/指令硬残留 + Markdown/对称模板软残留） ----
    res_hits = residue_scan(text)
    res_hard = [h for h in res_hits if h["type"] == "hard"]
    res_soft = [h for h in res_hits if h["type"] != "hard"]
    result["checks"]["残留痕迹"] = {
        "value": f"{len(res_hits)}处（硬{len(res_hard)}/软{len(res_soft)}）",
        "pass": len(res_hard) == 0,
        "note": "硬残留=AI对话/提示词痕迹，必须清除" if res_hard else ("软残留=格式/模板痕迹，建议清除" if res_soft else "无残留"),
    }
    if res_hard:
        for h in res_hard[:3]:
            result["issues"].append(f"第{h['line']}行残留AI对话痕迹: {h['pattern']}（硬残留，必须清除）")
    elif res_soft:
        for h in res_soft[:3]:
            result["issues"].append(f"第{h['line']}行疑似格式/模板残留: {h['pattern']}（建议清除）")

    # ---- 13. 统计特征（困惑度估算/突发性/词汇多样性/熵） ----
    ppl = perplexity_estimate(text)
    burst = burstiness_score(text)
    ttr = lexical_diversity(text)
    ent = text_entropy(text)
    stat_warn = []
    if ppl is not None and ppl < 50:
        stat_warn.append(f"困惑度估算{ppl}/100偏低（套话词密集/可预测性强）")
    if burst is not None and burst < 40:
        stat_warn.append(f"突发性{burst}/100偏低（句长过于均匀）")
    if ttr is not None and ttr < 45:
        stat_warn.append(f"词汇多样性{ttr}/100偏低（用词重复）")
    result["checks"]["统计特征"] = {
        "value": f"困惑度{ppl}/突发性{burst}/TTR{ttr}/熵{ent}",
        "pass": not stat_warn,
        "note": "；".join(stat_warn) if stat_warn else "统计特征正常",
    }
    if stat_warn:
        result["issues"].append("；".join(stat_warn))

    # ---- 汇总 ----
    result["pass"] = len(result["issues"]) == 0 and len(red_hits) == 0
    graded = [c for c in result["checks"].values() if isinstance(c, dict) and c.get("pass") is not None]
    passed = [c for c in graded if c.get("pass")]
    result["score"] = round(len(passed) / len(graded) * 100) if graded else 0
    result["anti_ai_score"] = anti_ai

    if output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"📖 质量检测 v1.0.5: {filepath}")
        print(f"  🌐 语言: {lang} | 安全: {'✅ 通过' if result['safety']['pass'] else '❌ 拦截'}")
        for k, v in result["checks"].items():
            if isinstance(v, dict):
                m = "✅" if v.get("pass") else ("➖" if v.get("pass") is None else "❌")
                note = f" ({v.get('note')})" if v.get("note") else ""
                print(f"  {m} {k}: {v.get('value', '')}{note}")
            else:
                print(f"  ℹ️  {k}: {v}")
        print(f"\n  硬性指标通过率: {result['score']}/100 {'✅ PASS' if result['pass'] else '❌ FAIL'}")
        print(f"  反AI评分: {anti_ai}/100 {'✅' if anti_ai >= 80 else '❌'}")
        if result["issues"]:
            for i in result["issues"]:
                print(f"    ⚠️ {i}")


if __name__ == "__main__":
    main()
