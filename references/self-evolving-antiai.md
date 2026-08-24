# 自进化反AI系统

> 模块F参考文档：动态黑名单 + 模式学习 + 版本追踪 + 社区贡献

---

## 一、系统架构

```
用户文本 ──→ 反AI引擎 ──→ 去AI化文本
     │                          │
     │                     用户反馈
     │                          │
     │                    ┌─────┴─────┐
     │                    ▼           ▼
     │              正面反馈      负面反馈
     │              (效果好)      (仍有AI味)
     │                    │           │
     │                    ▼           ▼
     │              确认当前规则  残留AI模式分析
     │                    │           │
     │                    │     ┌─────┴─────┐
     │                    │     ▼           ▼
     │                    │  新模式提取  失败原因归因
     │                    │     │           │
     │                    │     └─────┬─────┘
     │                    │           ▼
     │                    │     规则候选生成
     │                    │           │
     │                    │           ▼
     │                    │     验证测试
     │                    │     ┌─────┴─────┐
     │                    │     ▼           ▼
     │                    │  验证通过    验证失败
     │                    │     │           │
     │                    │     ▼           ▼
     │                    │  加入黑名单   丢弃/修改
     │                    │     │
     └────────────────────┴─────┘
                    │
                    ▼
              版本保持锁定 v1.0.5（只写进化日志）
```

---

## 二、动态黑名单机制

### 2.1 黑名单结构

```yaml
blacklist:
  version: v1.0.5
  last_updated: "2026-08-15"
  rules:
    - id: "zh-001"
      category: "逻辑连接词"
      pattern: "首先|其次|最后"
      replacement: "直接句号另起"
      language: "zh"
      source: "initial"
      confidence: 1.0
      usage_count: 0
      success_rate: 0.0

    - id: "en-001"
      category: "logical_connectors"
      pattern: "firstly|secondly|thirdly|lastly|finally"
      replacement: "direct_statement"
      language: "en"
      source: "initial"
      confidence: 1.0
      usage_count: 0
      success_rate: 0.0

    - id: "ja-001"
      category: "接続詞"
      pattern: "まず|次に|最後に|要するに|したがって|それゆえ"
      replacement: "行動描写切断"
      language: "ja"
      source: "initial"
      confidence: 1.0
      usage_count: 0
      success_rate: 0.0

    - id: "ko-001"
      category: "접속사"
      pattern: "먼저|다음으로|마지막으로|요컨대|따라서|그러므로"
      replacement: "행동묘사절단"
      language: "ko"
      source: "initial"
      confidence: 1.0
      usage_count: 0
      success_rate: 0.0
```

> 说明：以上示例仅为结构展示，**以 `references/antiai_blacklist.json` 为唯一权威数据源**（zh-001 已按版本演进去重移除"综上所述"，该词归 zh-005 总结性套话类）。

### 2.2 规则生命周期

```
新增规则 → 待验证(confidence=0.3) → 验证通过(confidence≥0.8) → 正式规则
                                      ↘ 验证失败 → 调整或丢弃
```

- **confidence 0.3**：新增待验证，仅标记不强制替换
- **confidence 0.5-0.7**：部分验证，建议替换
- **confidence ≥0.8**：充分验证，强制替换
- **confidence <0.3**：多次验证失败，标记为待删除

> 真实实现（evolve_blacklist.py）：低置信度规则（<1.0）每次被文本命中 +0.1 置信度（上限 1.0），
> usage_count 对所有规则按真实命中累加（初始规则同样累计）。
> 多语言候选发现：中/英/日/韩各语言内置 AI 高频短语种子池，文本中命中≥3次且不在黑名单时生成 confidence=0.3 待验证规则。

---

## 三、模式学习

### 3.1 从用户反馈学习

**触发**：用户反馈"还是有AI味"

**流程**：
1. 对比去AI化文本与用户标注的残留AI段
2. 提取残留段的统计特征（词频/句式/结构）
3. 与已知黑名单交叉，确认是否为新模式
4. 新模式 → 生成规则候选 → 加入待验证

### 3.2 从失败操作学习

**触发**：去AI化后反AI评分低于70分（统一标准，与 SKILL.md 8.7 一致）

**流程**：
1. 分析低分项（哪项检查未通过）
2. 定位问题文本段
3. 提取该段的AI特征模式
4. 归纳为可执行规则

### 3.3 模式提取模板

```yaml
new_pattern:
  detected_in: "文本摘要/段落索引"
  frequency: X次
  ai_features:
    - 特征1: "说明"
    - 特征2: "说明"
  candidate_rule:
    category: "新类别/现有类别"
    pattern: "正则或关键词"
    replacement: "替换策略"
    language: "zh/en/ja/ko"
    confidence: 0.3
```

---

## 四、版本追踪

### 4.1 版本命名规则

- 主版本.次版本.修订号（如 v1.0.5）
- **锁定策略（1.0.4 起）**：对外版本统一锁定为 v1.0.5，自进化只写进化日志、不递增版本号（避免与 SKILL.md/README/exports 文档漂移）
- 若未来有架构级变更需要版本递增，需同步更新全库文档版本号后统一发布

### 4.2 当前版本

| 项目 | 值 |
|------|-----|
| 版本 | v1.0.5 |
| 规则数 | 56（14类×4语言） |
| 最后更新 | 2026-08-15 |
| 验证通过率 | 待统计 |

### 4.3 版本记录格式

```yaml
version_log:
  - version: v1.0.0
    date: "2026-07-15"
    changes: "初始版本，14类AI词表中英双语"
    rule_count: 28

  - version: v1.0.1
    date: "2026-08-02"
    changes: "新增日韩词表、自进化机制、社区贡献预留"
    rule_count: 56
    new_rules:
      - ja-001~ja-014: "日文14类AI词表"
      - ko-001~ko-014: "韩文14类AI词表"

  - version: v1.0.2
    date: "2026-08-05"
    changes: "新增内容安全合规模块；统一反AI评分标准；配置格式修正；语言覆盖诚实声明；清理敏感内容"
    rule_count: 56

  - version: v1.0.3
    date: "2026-08-11"
    changes: "版本统一升级，合规声明客观化，语言覆盖校正，作家库补全，脚本优化"
    rule_count: 56

  - version: v1.0.5
    date: "2026-08-15"
    changes: "全面优化：单一数据源、多语言种子池、使用计数、规则去重"
    rule_count: 56
```

---

## 五、社区贡献框架（预留）

### 5.1 贡献接口

```yaml
community_contribution:
  status: "预留接口，暂未开放"
  planned_features:
    - 在线AI模式提交
    - 模式投票验证
    - 贡献者积分
    - 模式质量评分
  submission_format:
    pattern: "AI模式关键词/正则"
    language: "zh/en/ja/ko"
    category: "类别"
    example_text: "示例文本"
    suggested_replacement: "建议替换"
```

### 5.2 验证流程（未来）

```
社区提交 → 初步审核 → 小范围测试 → 投票验证 → 加入黑名单
```

---

## 六、进化日志模板

```yaml
evolution_log:
  date: "YYYY-MM-DD"
  trigger: "用户反馈/自动检测/手动触发"
  before:
    version: vX.Y.Z
    rule_count: N
    avg_anti_ai_score: XX
  analysis:
    texts_scanned: X
    new_patterns_found: X
    failed_operations_analyzed: X
  actions:
    - action: "add_rule"
      rule_id: "xx-NNN"
      category: "类别"
      pattern: "模式"
      confidence: 0.3
    - action: "upgrade_confidence"
      rule_id: "xx-NNN"
      from: 0.3
      to: 0.8
  after:
    version: v1.0.5（锁定，不递增）
    rule_count: N+X
    estimated_anti_ai_score: XX
```
