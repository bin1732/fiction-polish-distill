#!/usr/bin/env python3
"""fingerprint.py — 作者指纹提取与保留检测

作者指纹 = 个人化的表达习惯（高频用词/断句偏好/标点习惯/口头禅）。
润色与去味必须以"保留作者指纹"为前提——指纹被抹平 = 丧失个性化 = 偏离原创性。

功能:
    extract: 从参考文本提取作者指纹（高频 2-gram / 标点习惯 / 平均句长 / 口头禅）
    compare: 对比去味/润色前后的指纹保留度，报告哪些作者特征被保留/丢失
    protect: 对目标文本做指纹保护检查（作者高频词是否被替换，给出恢复提示）

用法:
    python3 fingerprint.py extract <作者参考文本.md>          # 提取指纹
    python3 fingerprint.py compare <原文.md> <处理后.md>      # 对比指纹保留度
    python3 fingerprint.py protect <指纹.json> <处理后.md>    # 检查指纹保护情况

说明: 全部为确定性统计，零外部依赖；指纹保留报告供流程方参考，
      规则化自动"注入"可能引入语义风险，本工具如实报告保留度而不伪造注入效果。
"""

import json
import re
import sys
from pathlib import Path

VERSION = "1.0.5"

# 中文高频停用词（不参与指纹统计）
STOPWORDS = {
    "的", "了", "是", "在", "和", "也", "都", "就", "他", "她", "我", "你", "它",
    "一个", "没有", "这个", "那个", "我们", "你们", "他们", "她们", "自己", "什么",
    "这样", "那样", "因为", "所以", "但是", "然后", "现在", "已经", "可以", "还是",
    "不是", "就是", "着", "过", "把", "被", "让", "给", "对", "从", "到", "向", "跟",
    "又", "再", "才", "便", "却", "而", "与", "或", "且", "并", "则", "之", "其", "所",
    "么", "呀", "呢", "吗", "吧", "啊", "哦", "嗯", "唉", "哎",
    "说", "想", "看", "走", "来", "去", "有", "做", "用", "地", "得",
    "您", "咱", "谁", "哪", "怎么", "如何", "哪里", "这里", "那里", "这些", "那些",
    "咱们", "人家", "大家", "自个儿", "彼此",
}
DASH_PAT = re.compile(r"——|—|--")
ELLIPSIS_PAT = re.compile(r"……|\.\.\.|···")
BANG_PAT = re.compile(r"[！!]")
QUESTION_PAT = re.compile(r"[？?]")
SENT_SPLIT = re.compile(r"(?<=[。！？；.!?])")


def _bigrams(text):
    """2-gram 词块（去空格/标点）。"""
    clean = re.sub(r"[\s，。！？；：、\"\"''（）()《》〈〉【】—…~-]", "", text)
    return [clean[i:i + 2] for i in range(len(clean) - 1) if clean[i:i + 2] not in STOPWORDS]


def extract(text):
    """提取作者指纹。"""
    bigrams = _bigrams(text)
    freq = {}
    for g in bigrams:
        freq[g] = freq.get(g, 0) + 1
    top = sorted(freq.items(), key=lambda x: -x[1])[:12]
    top_words = [w for w, c in top if c >= 2][:8]
    # 口头禅：出现 ≥3 次且长度 2-3 的独有词块（排除停用词）
    pet_phrases = [w for w, c in sorted(freq.items(), key=lambda x: -x[1])[:20] if c >= 3][:4]
    sents = [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]
    avg_len = round(sum(len(s) for s in sents) / len(sents), 1) if sents else 0
    total = len(text)
    dash = len(DASH_PAT.findall(text)) * 1000 / total if total else 0
    ell = len(ELLIPSIS_PAT.findall(text)) * 1000 / total if total else 0
    bang = len(BANG_PAT.findall(text)) * 1000 / total if total else 0
    question = len(QUESTION_PAT.findall(text)) * 1000 / total if total else 0
    return {
        "version": VERSION,
        "top_words": top_words,
        "pet_phrases": pet_phrases,
        "avg_sentence_len": avg_len,
        "dash_per_thousand": round(dash, 1),
        "ellipsis_per_thousand": round(ell, 1),
        "bang_per_thousand": round(bang, 1),
        "question_per_thousand": round(question, 1),
    }


def compare(orig_text, new_text):
    """对比指纹保留度：返回保留/丢失/新增特征。"""
    fp_orig = extract(orig_text)
    fp_new = extract(new_text)
    lost = [w for w in fp_orig["top_words"] if w not in fp_new["top_words"]]
    kept = [w for w in fp_orig["top_words"] if w in fp_new["top_words"]]
    return {
        "fingerprint_orig": fp_orig,
        "fingerprint_new": fp_new,
        "top_words_kept": kept,
        "top_words_lost": lost,
        "note": (
            "作者高频词丢失过多 → 润色/去味可能抹平了个人风格，建议恢复原作者的表达习惯"
            if len(lost) >= 3 and len(fp_orig["top_words"]) >= 4
            else "作者指纹保留良好"
        ),
    }


def protect(fp, new_text):
    """指纹保护检查：作者高频词/口头禅在目标文本中的保留情况。"""
    missing = [w for w in fp.get("top_words", []) if w not in new_text]
    pets_missing = [w for w in fp.get("pet_phrases", []) if w not in new_text]
    report = {
        "version": VERSION,
        "missing_top_words": missing,
        "missing_pet_phrases": pets_missing,
        "advice": (
            "以下作者指纹特征在处理后丢失，建议按原风格恢复: " + "、".join((missing + pets_missing)[:6])
            if missing or pets_missing
            else "作者指纹特征完整保留"
        ),
    }
    return report


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "extract" and len(argv) >= 2:
        p = Path(argv[1])
        if not p.exists():
            print(f"文件不存在: {argv[1]}")
            return 1
        text = p.read_text(encoding="utf-8", errors="replace")
        print(json.dumps(extract(text), ensure_ascii=False, indent=2))
        return 0
    if cmd == "compare" and len(argv) >= 3:
        a = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
        b = Path(argv[2]).read_text(encoding="utf-8", errors="replace")
        print(json.dumps(compare(a, b), ensure_ascii=False, indent=2))
        return 0
    if cmd == "protect" and len(argv) >= 3:
        fp = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        t = Path(argv[2]).read_text(encoding="utf-8", errors="replace")
        print(json.dumps(protect(fp, t), ensure_ascii=False, indent=2))
        return 0
    print(f"未知命令: {cmd}（可用: extract/compare/protect）")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
