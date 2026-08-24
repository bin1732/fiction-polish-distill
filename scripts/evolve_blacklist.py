#!/usr/bin/env python3
"""evolve_blacklist.py — 自进化反AI黑名单管理器 v1.0.5

用法:
    python3 evolve_blacklist.py add "AI模式" --lang zh --category "逻辑连接词" [--replacement "替换策略"]
    python3 evolve_blacklist.py scan <文件.md>              # 扫描命中（只读）
    python3 evolve_blacklist.py stats                       # 统计概览
    python3 evolve_blacklist.py top 10                      # 最常用规则（按 usage_count）
    python3 evolve_blacklist.py evolve <目录/>              # 自进化：扫描文本+发现新模式+更新usage
    python3 evolve_blacklist.py export [--format json|yaml|md]
    python3 evolve_blacklist.py report                      # 进化报告

数据源: 唯一数据源为 references/antiai_blacklist.json（本脚本不再内置第二份词表）。
自进化: 多语言（中/英/日/韩）候选模式发现，基于内置种子池在文本中的命中验证，诚实标记 confidence=0.3 待验证。
"""

import re
import sys
import json
import os
from pathlib import Path
from datetime import datetime

BLACKLIST_FILE = Path(__file__).parent.parent / "references" / "antiai_blacklist.json"

SUPPORTED_LANGS = {"zh", "en", "ja", "ko"}

# 各语言候选 AI 模式池（种子启发式，供 evolve 在文本中验证；发现后仍需人工/验证流程确认）
# 注意：已与 antiai_blacklist.json 现有规则交叉比对，池中不重复收录黑名单已有短语
# （黑名单已有：众所周知/总而言之/综上所述/值得注意的是/换句话说/要するに/요컨대 等）。
CANDIDATE_POOLS = {
    "zh": [
        "不可否认的是", "毫无疑问", "不言而喻", "显而易见", "与此同时",
        "在这种背景下", "从某种程度上来说", "不难发现",
        "由此可见", "在一定程度上", "某种意义上", "我们需要认识到", "这不仅仅",
        "最重要的是", "值得一提的是", "不难看出", "从某种意义上讲",
    ],
    "en": [
        "it is important to note", "it should be noted", "it is worth noting",
        "needless to say", "without a doubt", "last but not least",
        "it is evident that", "as previously mentioned", "in this day and age",
        "it goes without saying", "at the end of the day", "when it comes to",
    ],
    "ja": [
        "言うまでもなく", "言い換えれば", "まとめると",
        "明らかに", "疑いなく", "重要なのは", "注目すべきは", "とはいえ", "確かに",
    ],
    "ko": [
        "말할 것도 없이", "정리하면",
        "명백히", "의심할 여지 없이", "중요한 것은", "주목할 점은", "확실히",
    ],
}


def load_blacklist():
    """从 JSON 读取（唯一数据源）。文件缺失/损坏时明确报错退出。"""
    if not BLACKLIST_FILE.exists():
        print(f"❌ 黑名单文件不存在: {BLACKLIST_FILE}")
        print("  请确认 skill 目录结构完整（需要 references/antiai_blacklist.json）")
        sys.exit(2)
    try:
        return json.loads(BLACKLIST_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"❌ 黑名单 JSON 解析失败: {e}")
        sys.exit(2)


def save_blacklist(data):
    """写回 JSON（唯一数据源）。"""
    BLACKLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    BLACKLIST_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def next_id(data, lang):
    """生成形如 zh-015 的下一个 ID（自动跳过已占用）。"""
    existing = {r["id"] for r in data["rules"]}
    n = 1
    while f"{lang}-{n:03d}" in existing:
        n += 1
    return f"{lang}-{n:03d}"


def compile_pattern(pattern, lang):
    """编译规则正则；英文忽略大小写（句首大写），非法正则抛错。"""
    flags = re.IGNORECASE if lang == "en" else 0
    return re.compile(pattern, flags)


def validate_pattern(pattern, lang):
    """校验正则合法性，返回 (ok, error)。"""
    try:
        compile_pattern(pattern, lang)
        return True, None
    except re.error as e:
        return False, str(e)


def cmd_add(args):
    """添加规则：add <pattern> [--lang zh] [--category 类别] [--replacement 策略]"""
    data = load_blacklist()
    pattern = None
    lang = "zh"
    category = "未分类"
    replacement = ""

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--lang" and i + 1 < len(args):
            lang = args[i + 1]
            i += 2
            continue
        elif a == "--category" and i + 1 < len(args):
            category = args[i + 1]
            i += 2
            continue
        elif a == "--replacement" and i + 1 < len(args):
            replacement = args[i + 1]
            i += 2
            continue
        elif a.startswith("--"):
            print(f"❌ 未知选项: {a}")
            return
        else:
            if pattern is None:
                pattern = a
            else:
                print(f"❌ 多余的位置参数: {a}（pattern 只能有一个）")
                return
        i += 1

    if pattern is None:
        print("❌ 缺少 pattern：add \"AI模式\" --lang zh --category 类别")
        return
    if lang not in SUPPORTED_LANGS:
        print(f"❌ 不支持的语言: {lang}（支持: {','.join(sorted(SUPPORTED_LANGS))}）")
        return

    ok, err = validate_pattern(pattern, lang)
    if not ok:
        print(f"❌ 非法正则: {err}")
        return

    # 防重复：pattern 已存在则提示
    for r in data["rules"]:
        if r["pattern"] == pattern and r["language"] == lang:
            print(f"⏭️  规则已存在: {r['id']} [{r['category']}] {pattern}，跳过")
            return

    rule = {
        "id": next_id(data, lang),
        "category": category,
        "pattern": pattern,
        "replacement": replacement or "人工确认替换策略",
        "language": lang,
        "source": "user_added",
        "confidence": 0.3,
        "usage_count": 0,
        "success_rate": 0.0,
    }
    data["rules"].append(rule)
    save_blacklist(data)
    print(f"✅ 已添加规则 {rule['id']}: [{category}] {pattern} (confidence=0.3，待验证)")


def cmd_scan(args):
    """扫描文本命中黑名单模式（只读，不写回）。"""
    if not args:
        print("用法: evolve_blacklist.py scan <文件.md>")
        return

    data = load_blacklist()
    filepath = args[0]
    if not os.path.isfile(filepath):
        print(f"❌ 找不到文件: {filepath}")
        return
    try:
        text = Path(filepath).read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return
    total = len(text)

    print(f"🔍 扫描: {filepath}")
    print(f"   文本长度: {total}字")
    print()

    hits = []
    for rule in data["rules"]:
        try:
            rx = compile_pattern(rule["pattern"], rule["language"])
            matches = rx.findall(text)
        except re.error:
            continue
        if matches:
            hits.append((rule, matches))

    if not hits:
        print("  ✅ 未检测到已知AI模式")
        return

    for rule, matches in sorted(hits, key=lambda x: len(x[1]), reverse=True):
        print(f"  ❌ [{rule['id']}] {rule['category']}: '{rule['pattern']}' → {len(matches)}次")
        for m in matches[:5]:
            print(f"     - {m}")
        if len(matches) > 5:
            print(f"     ... 及其他{len(matches) - 5}处")

    print(f"\n  总计: {len(hits)}类AI模式, {sum(len(m) for _, m in hits)}处匹配")


def cmd_stats(args):
    """统计概览。"""
    data = load_blacklist()
    print(f"📊 反AI黑名单统计 — {data['version']}")
    print(f"   最后更新: {data['last_updated']}")
    print(f"   总规则数: {len(data['rules'])}")
    print()

    by_lang = {}
    by_category = {}
    by_confidence = {"高(≥0.8)": 0, "中(0.5-0.8)": 0, "低(<0.5)": 0}
    total_usage = 0

    for r in data["rules"]:
        by_lang[r["language"]] = by_lang.get(r["language"], 0) + 1
        by_category[r["category"]] = by_category.get(r["category"], 0) + 1
        c = r["confidence"]
        if c >= 0.8:
            by_confidence["高(≥0.8)"] += 1
        elif c >= 0.5:
            by_confidence["中(0.5-0.8)"] += 1
        else:
            by_confidence["低(<0.5)"] += 1
        total_usage += r.get("usage_count", 0)

    print("  按语言:")
    lang_names = {"zh": "中文", "en": "英文", "ja": "日文", "ko": "韩文"}
    for lang, count in sorted(by_lang.items()):
        print(f"    {lang_names.get(lang, lang)}: {count}条")

    print("\n  按置信度:")
    for level, count in by_confidence.items():
        print(f"    {level}: {count}条")

    print("\n  按类别 (Top10):")
    for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {cat}: {count}条")

    print(f"\n  累计使用次数: {total_usage}")


def cmd_top(args):
    """按 usage_count 输出最常用规则（真实数据，由 evolve 累计）。"""
    data = load_blacklist()
    try:
        n = int(args[0]) if args else 10
    except (ValueError, IndexError):
        print(f"❌ 无效数量: {args[0] if args else '(空)'}")
        return
    if n <= 0:
        print(f"❌ 数量必须为正整数: {n}")
        return

    sorted_rules = sorted(data["rules"], key=lambda r: r.get("usage_count", 0), reverse=True)[:n]

    print(f"🔝 Top {n} 最常用规则:")
    for i, r in enumerate(sorted_rules, 1):
        print(f"  {i}. [{r['id']}] {r['category']}: '{r['pattern']}' (使用{r.get('usage_count', 0)}次, "
              f"成功率{r.get('success_rate', 0):.0%}, conf={r['confidence']})")


def cmd_evolve(args):
    """自进化：扫描目录内 .md/.txt 文本，完成三件事：
    1. 所有规则 usage_count 按真实命中累加（不再只统计低置信度规则）
    2. 从文本中发现种子池候选模式（多语言），自动加入 confidence=0.3 待验证
    3. 进化日志（版本锁定 v1.0.5，不递增）
    """
    if not args:
        print("用法: evolve_blacklist.py evolve <目录/>")
        return

    data = load_blacklist()
    directory = Path(args[0])
    if not directory.exists():
        print(f"❌ 目录不存在: {directory}")
        return
    if not directory.is_dir():
        print(f"❌ 不是目录: {directory}")
        return

    md_files = list(directory.glob("**/*.md")) + list(directory.glob("**/*.txt"))
    if not md_files:
        print(f"⚠️ 目录中无 .md/.txt 文件: {directory}")
        return

    print(f"🧬 自进化扫描: {directory}")
    print(f"   扫描文件: {len(md_files)}个")
    print()

    all_text = ""
    for f in md_files:
        try:
            all_text += f.read_text(encoding="utf-8") + "\n"
        except Exception as e:
            print(f"  ⚠️ 跳过文件 {f.name}: {e}")

    total_chars = len(all_text)
    if total_chars < 100:
        print("  ⚠️ 文本总量过小(<100字)，无法有效学习，跳过")
        return

    # ---- 1. usage_count 真实累加（全部规则，含初始规则） ----
    usage_before = sum(r.get("usage_count", 0) for r in data["rules"])
    usage_before_rules = len(data["rules"])
    for rule in data["rules"]:
        try:
            rx = compile_pattern(rule["pattern"], rule["language"])
            n_hits = len(rx.findall(all_text))
        except re.error:
            continue
        rule["usage_count"] = rule.get("usage_count", 0) + n_hits
        if n_hits > 0 and rule["confidence"] < 1.0:
            # 命中即证据：低置信度规则每次命中 +0.1，上限 1.0
            rule["confidence"] = min(rule["confidence"] + 0.1, 1.0)
    usage_after = sum(r.get("usage_count", 0) for r in data["rules"])

    # ---- 2. 多语言候选模式发现 ----
    # 机制：种子池验证。各语言预置 AI 高频短语池，在文本中命中≥3次且不在黑名单
    # 时，生成 confidence=0.3 的待验证规则。不做无监督 n-gram 发现，避免把
    # "that"/"다." 这类普通高频词误判为 AI 模式（避免假发现）。
    discovered = []
    existing_patterns = {(r["language"], r["pattern"]) for r in data["rules"]}
    for lang, pool in CANDIDATE_POOLS.items():
        for phrase in pool:
            if (lang, phrase) in existing_patterns:
                continue
            rx = compile_pattern(re.escape(phrase), lang)
            count = len(rx.findall(all_text))
            if count >= 3:
                new_id = next_id(data, lang)
                rule = {
                    "id": new_id,
                    "category": "自进化发现",
                    "pattern": phrase,
                    "replacement": "人工确认替换策略",
                    "language": lang,
                    "source": "auto_evolve",
                    "confidence": 0.3,
                    "usage_count": count,
                    "success_rate": 0.0,
                }
                data["rules"].append(rule)
                discovered.append(f"  🆕 {new_id}: '{phrase}' → 出现{count}次 (confidence=0.3, {lang})")

    # ---- 3. 版本递增与日志（仅在确有变化时） ----
    changed = len(discovered) > 0 or usage_after > usage_before
    if not changed:
        print("  无新发现模式，usage_count 无变化，版本保持不变")
        return

    # 版本锁定策略：本 skill 对外版本统一锁定为 v1.0.5（SKILL.md/README/exports 全库一致）。
    # 自进化只写进化日志，不递增主版本号，避免文档与黑名单版本漂移。
    data["version"] = "v1.0.5"
    data["evolution_log"].append({
        "version": "v1.0.5",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "changes": f"自进化扫描{len(md_files)}文件，发现{len(discovered)}个候选模式，usage累计+{usage_after - usage_before}",
        "rule_count": len(data["rules"]),
    })

    save_blacklist(data)

    print("  版本: v1.0.5（锁定，不递增）")
    print(f"  规则数: {usage_before_rules} → {len(data['rules'])}")
    print(f"  usage_count 累计: +{usage_after - usage_before} 次命中")
    print()

    if discovered:
        print("  新发现候选模式:")
        for p in discovered[:15]:
            print(p)
        if len(discovered) > 15:
            print(f"  ... 及其他{len(discovered) - 15}个")
    else:
        print("  无新发现模式（仅更新 usage_count）")

    print("\n  ✅ 进化完成 → v1.0.5（锁定版本）")
    print("  ⚠️ 新增规则均为 confidence=0.3 待验证，请人工确认替换策略后再用")


def cmd_export(args):
    """导出黑名单为 json/yaml/md。"""
    data = load_blacklist()
    fmt = "json"
    if args and args[0] == "--format" and len(args) > 1:
        fmt = args[1]
    elif args and args[0] != "--format":
        fmt = args[0]

    if fmt == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif fmt == "yaml":
        print(f"version: {data['version']}")
        print(f"last_updated: {data['last_updated']}")
        print("rules:")
        for r in data["rules"]:
            # YAML 标量含特殊字符（: | # "）时加引号，避免 YAML 解析失败
            def yq(s):
                s = str(s)
                return f'"{s}"' if re.search(r"[:|#\"'\n]", s) else s
            print(f"  - id: {r['id']}")
            print(f"    category: {yq(r['category'])}")
            print(f"    pattern: {yq(r['pattern'])}")
            print(f"    replacement: {yq(r['replacement'])}")
            print(f"    language: {r['language']}")
            print(f"    confidence: {r['confidence']}")
            print(f"    usage_count: {r.get('usage_count', 0)}")
            print(f"    success_rate: {r.get('success_rate', 0.0)}")
            print(f"    source: {r.get('source', 'initial')}")
    elif fmt == "md":
        print(f"# 反AI黑名单 {data['version']}")
        print(f"\n> 最后更新: {data['last_updated']}")
        print("\n| ID | 语言 | 类别 | 模式 | 替换策略 | 置信度 | 使用次数 |")
        print("|-----|------|------|------|----------|--------|----------|")
        for r in data["rules"]:
            # pattern 中的 | 是正则分隔符，需转义为 \| 以免破坏 Markdown 表格列
            esc_pat = r["pattern"].replace("|", "\\|")
            esc_rep = r["replacement"].replace("|", "\\|")
            print(f"| {r['id']} | {r['language']} | {r['category']} | `{esc_pat}` | "
                  f"{esc_rep} | {r['confidence']} | {r.get('usage_count', 0)} |")
    else:
        print(f"❌ 未知格式: {fmt}（支持: json|yaml|md）")


def cmd_report(args):
    """进化报告。"""
    data = load_blacklist()
    print(f"📋 进化报告 — {data['version']}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    print(f"  当前版本: {data['version']}")
    print(f"  最后更新: {data['last_updated']}")
    print(f"  总规则数: {len(data['rules'])}")
    print()

    by_lang = {}
    for r in data["rules"]:
        by_lang[r["language"]] = by_lang.get(r["language"], 0) + 1

    lang_names = {"zh": "中文", "en": "英文", "ja": "日文", "ko": "韩文"}
    print("  语言分布:")
    for lang, count in sorted(by_lang.items()):
        print(f"    {lang_names.get(lang, lang)}: {count}条")
    print()

    by_source = {}
    for r in data["rules"]:
        by_source[r.get("source", "initial")] = by_source.get(r.get("source", "initial"), 0) + 1

    print("  来源分布:")
    source_names = {"initial": "初始规则", "user_added": "用户添加", "auto_evolve": "自进化发现", "community": "社区贡献"}
    for source, count in sorted(by_source.items()):
        print(f"    {source_names.get(source, source)}: {count}条")
    print()

    avg_confidence = sum(r["confidence"] for r in data["rules"]) / len(data["rules"]) if data["rules"] else 0
    print(f"  平均置信度: {avg_confidence:.2f}")

    total_usage = sum(r.get("usage_count", 0) for r in data["rules"])
    print(f"  总使用次数: {total_usage}")
    print()

    print("  版本历史:")
    for entry in data["evolution_log"]:
        print(f"    {entry['version']} ({entry['date']}): {entry['changes']} ({entry['rule_count']}条)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "add": cmd_add,
        "scan": cmd_scan,
        "stats": cmd_stats,
        "top": cmd_top,
        "evolve": cmd_evolve,
        "export": cmd_export,
        "report": cmd_report,
    }

    if command in commands:
        commands[command](args)
    else:
        print(f"未知命令: {command}")
        print(f"可用命令: {', '.join(commands.keys())}")
