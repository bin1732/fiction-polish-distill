<div align="center">

# fiction-polish-distill

**小说润色蒸馏专家** — 反AI去味 · 智能润色 · 风格蒸馏 · 作家仿写 · 多语言适配 · 自进化 · 专家团会诊

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.5-green.svg)](SKILL.md)
[![Languages](https://img.shields.io/badge/languages-中%2F%E8%8B%B1%2F%E6%97%A5%2F%E9%9F%A9-orange.svg)](#多语言支持)
[![Platforms](https://img.shields.io/badge/platforms-Claude%20Code%20%7C%20OpenClaw%20%7C%20ChatGPT%20%7C%20DeepSeek%20%7C%20Gemini%20%7C%20Kimi-lightgrey.svg)](#)

</div>

> 七位一体的小说创作质量提升工具，覆盖全球全类型小说。纯本地规则库驱动，零外部依赖。

## ✨ 特性

- 🧹 **反AI去味** — 多维度质量检测 + 针对性改写，降低AI文本痕迹
- ✍️ **智能润色** — 内置润色规则库，按文体 / 场景 / 平台精准优化
- 🔬 **风格蒸馏** — 从样本提取写作风格，生成可复用风格档案
- 🎭 **作家仿写** — 多位作家风格模型，支持定向仿写
- 🌏 **多语言适配** — 中英日韩四语深度适配，60种语言自动检测
- 🧠 **自进化反AI** — 黑名单持续学习，自适应检测更新
- 👥 **专家团会诊** — 多角度交叉审查，模拟多专家联合评估

## 🌍 覆盖范围

| 语种/地区 | 覆盖品类 |
|-----------|----------|
| 🇨🇳 中国网文 | 玄幻 / 都市 / 言情 / 悬疑 / 科幻 / 历史 / 武侠 / 游戏 / 轻小说 / 种田 / 恐怖 / 百合BL |
| 🇺🇸 英文小说 | Romance / Fantasy / Sci-Fi / Thriller / Horror / Mystery / YA / LitRPG / Historical / Women's Fiction |
| 🇯🇵 日本轻小说 | 異世界 / 転生 / ラブコメ / ダークファンタジー |
| 🇰🇷 韩国网文 | 로판 / 회귀 / 먼치킨 / 게임판타지 |
| 📚 出版文学 | 严肃文学 / 通俗小说 / 类型文学 |

## 🚀 快速开始

在支持 OpenClaw / Codex CLI / ChatGPT / Claude Code / DeepSeek / Gemini / Kimi 的环境中加载本技能后即可使用。

```
# 常见触发方式
去AI味：    "去AI味" / "去掉机器感" / "de-AI this"
润色：      "润色" / "polish this" / "更自然一点"
风格蒸馏：  "提取我的风格" / "extract my style" / "学我的写法"
作家仿写：  "用鲁迅风格改写" / "imitate Hemingway"
专家会诊：  "专家会诊一下这段" / "多维度评估"
```

## 📁 项目结构

```
fiction-polish-distill/
├── SKILL.md                          # 技能主文档
├── references/                       # 规则库与指南（20+ 份）
│   ├── de-ai-engine.md               # 反AI引擎原理
│   ├── distillation-engine.md        # 风格蒸馏框架
│   ├── polish-rules.md               # 润色规则库
│   ├── writer-styles.md              # 作家风格模型
│   ├── platform-fiction-rules.md     # 各平台规范
│   ├── antiai_blacklist.json         # 反AI黑名单
│   └── ...
└── scripts/                          # Python 工具脚本
    ├── deai_loop.py                  # 反AI循环优化
    ├── quality_check.py              # 质量多维度检测
    ├── fingerprint.py                # 风格指纹提取
    ├── narrative_check.py            # 叙事结构检查
    ├── platform_policy_check.py      # 平台规范核查
    └── evolve_blacklist.py           # 反AI黑名单进化
```

## 📝 说明

本工具为写作辅助工具，旨在提升文本质量与自然度。无法保证通过任何平台的 AI 检测（检测技术持续升级），使用者需自行遵守各平台的内容政策与规范声明义务。

## License | 许可证

本项目采用 **MIT License** 开源许可协议 — 您可以自由地使用、复制、修改、合并、发布、分发、再许可和/或出售本软件的副本，但须在所有副本或重要部分中包含上述版权声明和本许可声明。

完整协议文本请查看 [LICENSE](LICENSE) 文件。
