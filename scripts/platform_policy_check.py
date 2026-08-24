#!/usr/bin/env python3
"""platform_policy_check.py — 平台 AI 创作规范联网核实工具

联网实时核实各大小说平台与监管机构对 AI 辅助创作的最新规范，
作为技能处理时的真实依据（不依赖任何第三方库，仅标准库）。

用法:
    python3 platform_policy_check.py                    # 核实全部来源
    python3 platform_policy_check.py --platform jinjiang # 仅核实指定来源
    python3 platform_policy_check.py --refresh           # 强制刷新缓存（默认 24 小时有效）
    python3 platform_policy_check.py --json              # JSON 格式输出

来源说明:
    全部来源均为官方或权威公开页面（监管机构官网/平台官方公告/权威媒体转载），
    抓取结果如实输出；任一来源不可达时如实标记"未获取到最新信息，请人工核实"，
    绝不编造政策内容。

零外部依赖声明: 本脚本仅使用 Python 标准库（urllib/json/re/tempfile/os）。
"""

import json
import os
import re
import sys
import tempfile
import urllib.request
from datetime import datetime, timedelta

VERSION = "1.0.5"
CACHE_TTL_HOURS = 24

# 官方/权威来源清单（平台、标识、来源名称、URL、政策关键词提取规则）
SOURCES = [
    {
        "id": "jinjiang",
        "platform": "晋江文学城",
        "name": "《关于AI辅助写作使用、判定的试行公告》（官方公告，权威媒体全文转载）",
        "url": "https://news.qq.com/rain/a/20250218A07F5700",
        "keywords": ["校对", "要素", "粗纲", "锁章", "禁榜", "举报", "原创性", "60%"],
        "title_pattern": r"AI辅助写作",
    },
    {
        "id": "qidian",
        "platform": "起点中文网",
        "name": "《关于进一步加强对非真人自动化创作管理力度的公告》及持续治理报道",
        "url": "https://m.jiemian.com/article/14946731.html",
        "keywords": ["非真人", "自动化", "暂停推荐", "撤下榜单", "屏蔽", "下架", "公示", "检测"],
        "title_pattern": r"AI",
    },
    {
        "id": "fanqie",
        "platform": "番茄小说",
        "name": "AI 稿件收紧签约审查标准（2025-04 公告，权威媒体综述）",
        "url": "https://m.thepaper.cn/newsDetail_forward_31989458",
        "keywords": ["情节叙事不清", "结构混乱", "转折生硬", "逻辑割裂", "签约审查"],
        "title_pattern": r"AI",
    },
    {
        "id": "cac",
        "platform": "国家网信办",
        "name": "《人工智能生成合成内容标识办法》（官方法规）",
        "url": "https://www.gov.cn/zhengce/202503/content_7014404.htm",
        "keywords": ["显式标识", "隐式标识", "元数据", "生成合成内容", "疑似"],
        "title_pattern": r"标识",
    },
    {
        "id": "industry",
        "platform": "网络文学行业",
        "name": "16家平台《网络文学行业反洗稿自律公约》（2025-04-28，权威媒体）",
        "url": "https://www.guancha.cn/economy/2025_04_29_774125.shtml",
        "keywords": ["反洗稿", "自律公约", "AI辅助创作", "原创", "版权"],
        "title_pattern": r"反洗稿",
    },
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def cache_dir():
    """缓存目录：系统临时目录下的技能专属子目录（不污染技能包）。"""
    d = os.path.join(tempfile.gettempdir(), "fiction-polish-distill-cache")
    os.makedirs(d, exist_ok=True)
    return d


def cache_path(src_id):
    return os.path.join(cache_dir(), f"policy_{src_id}.json")


def load_cache(src_id):
    """读取缓存（24 小时内有效）。"""
    p = cache_path(src_id)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        fetched = datetime.fromisoformat(data.get("fetched_at", ""))
        if datetime.now() - fetched > timedelta(hours=CACHE_TTL_HOURS):
            return None
        return data
    except Exception:
        return None


def save_cache(src_id, data):
    try:
        with open(cache_path(src_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def fetch_url(url, timeout=15):
    """抓取页面 HTML。失败抛异常，由调用方如实处理。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def strip_html(html):
    """去除 HTML 标签与脚本样式，保留正文文本。"""
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?is)<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_points(text, source):
    """按关键词提取政策要点：命中关键词附近的句子，去重后输出。

    窗口内片段默认保留完整句；仅当片段超长（>160 字符）时才截断到
    最近的句子结束符（避免截掉句首字导致要点残缺）。
    """
    hits = set()
    for kw in source["keywords"]:
        for m in re.finditer(re.escape(kw), text):
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            snippet = text[start:end].strip()
            # 超长片段截断到最近句子结束符（保留完整句）
            if len(snippet) > 160:
                for sep in ("。", "！", "？", "；", "\n"):
                    idx = snippet.rfind(sep, 0, 150)
                    if idx > 0:
                        snippet = snippet[idx + 1:].strip()
                        break
            snippet = re.sub(r"\s+", " ", snippet)
            if 12 <= len(snippet) <= 180:
                hits.add(snippet)
            if len(hits) >= 6:
                break
    return sorted(hits)


def verify_source(source, refresh=False):
    """核实单个来源。返回结果字典（如实标记成功/失败）。"""
    src_id = source["id"]
    if not refresh:
        cached = load_cache(src_id)
        if cached:
            cached["from_cache"] = True
            return cached

    result = {
        "id": src_id,
        "platform": source["platform"],
        "name": source["name"],
        "url": source["url"],
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "status": "ok",
        "points": [],
        "error": "",
        "from_cache": False,
    }
    try:
        html = fetch_url(source["url"])
        text = strip_html(html)
        points = extract_points(text, source)
        if not points:
            # 页面结构变化导致关键词未命中：如实标记，不编造要点
            result["status"] = "partial"
            result["error"] = "已获取页面但未能提取政策要点（页面结构可能已更新），请人工核实"
        else:
            result["points"] = points
        save_cache(src_id, result)
    except Exception as e:
        result["status"] = "unreachable"
        result["error"] = f"未获取到最新信息（{type(e).__name__}: {str(e)[:60]}），请人工核实"
        save_cache(src_id, result)
    return result


def report(results, as_json=False):
    """输出核实报告。"""
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    print("══ 平台 AI 创作规范联网核实报告 ══")
    print(f"核实时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for r in results:
        tag = {"ok": "✅", "partial": "⚠", "unreachable": "❌"}.get(r["status"], "?")
        print(f"\n{tag} {r['platform']} — {r['name']}")
        print(f"   来源: {r['url']} | 抓取: {r['fetched_at']} {'(缓存)' if r.get('from_cache') else ''}")
        if r["status"] == "ok":
            for p in r["points"]:
                print(f"   · {p}")
        else:
            print(f"   {r['error']}")
    print("\n说明: 以上要点均来自官方/权威公开页面原文提取；请以各平台官方最新公告为准。")


def main(argv):
    import argparse

    parser = argparse.ArgumentParser(description="平台 AI 创作规范联网核实工具")
    parser.add_argument(
        "--platform",
        choices=[s["id"] for s in SOURCES],
        help="仅核实指定来源（jinjiang/qidian/fanqie/cac/industry）",
    )
    parser.add_argument("--refresh", action="store_true", help="强制刷新缓存（默认 24 小时有效）")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON 格式输出")
    args = parser.parse_args(argv)

    refresh = args.refresh
    as_json = args.as_json
    platform_only = args.platform

    targets = SOURCES
    if platform_only:
        targets = [s for s in SOURCES if s["id"] == platform_only]

    results = [verify_source(s, refresh) for s in targets]
    report(results, as_json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
