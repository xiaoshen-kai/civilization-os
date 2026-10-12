# 案例目录与检索

版本 2.0 有 1000 条记录：100 个 `deep_case` 和 900 个 `evidence_event`，共 2100 条主张。深度案例支持带局限的复盘；事实事件支持所存官方字段及进一步查源。结构和证据范围见 [evidence.md](evidence.md)。

## 当前分库

| ID 范围 | 数量／类型 | 文件 | 实际 domain | 来源与覆盖 |
| --- | --- | --- | --- | --- |
| C001 至 C010 | 10／deep_case | [cases.json](cases.json) | technology、business、organization、behavior_research、economic_research、learning_research | 原有工程、商业及研究案例 |
| C011 至 C060 | 50／deep_case | [cases-nasa-deep.json](cases-nasa-deep.json) | technology | NASA LLIS 官方 GitHub 固定版本；过去工程事件与经验记录 |
| C061 至 C090 | 30／deep_case | [cases-business-deep.json](cases-business-deep.json) | business、organization | CFPB 公开执法材料；具体行为、监管判断与处置边界 |
| C091 至 C100 | 10／deep_case | [cases-technology-deep.json](cases-technology-deep.json) | technology | 企业与机构公开技术故障复盘 |
| C101 至 C400 | 300／evidence_event | [cases-events-fdic.json](cases-events-fdic.json) | finance | FDIC 银行失败历史字段；生效年份不晚于 2025 |
| C401 至 C600 | 200／evidence_event | [cases-events-cfpb.json](cases-events-cfpb.json) | regulatory_action | CFPB 执法目录的标题、日期与链接；排除已收录的相关深度事件 |
| C601 至 C850 | 250／evidence_event | [cases-events-clinical.json](cases-events-clinical.json) | clinical_research | ClinicalTrials.gov 已完成的随机干预性研究；至少一个主要结果有测量值，结果首次 Posted 不晚于 2025-12-31 |
| C851 至 C1000 | 150／evidence_event | [cases-events-nobel.json](cases-events-nobel.json) | scientific_awards | 物理、化学、生理学或医学各 50 个年度奖项；奖项年份不晚于 2025，同年度类别的获奖人合并 |

`sources-*.json` 给出来源、核验日期、支持范围和局限。事实事件的最小字段快照在 [event-data/fdic.json](event-data/fdic.json)、[event-data/cfpb.json](event-data/cfpb.json)、[event-data/clinical.json](event-data/clinical.json)、[event-data/nobel.json](event-data/nobel.json)。快照保留精选记录和字段，不包含完整数据库；其 `selection_rule` 与 `retrievals` 说明取样和实际抓取版本。

NASA 的 `technology` 包括航空航天工程；没有单独的 `aerospace` 过滤值。模型分类用 `--domain`，案例分类用 `--case-domain`，两者不要混用。动态数量以 `catalog.py stats` 和 [manifest.json](manifest.json) 为准。

## 一次检索少量记录

把 `<skill-dir>` 换成 Skill 的绝对路径：

```text
python "<skill-dir>/scripts/catalog.py" search "失效" --cases --record-type deep_case --case-domain technology --limit 5
python "<skill-dir>/scripts/catalog.py" search "约束" --cases --record-type deep_case --model P007 --limit 5
python "<skill-dir>/scripts/catalog.py" search "监管" --cases --record-type evidence_event --case-domain regulatory_action --limit 5
python "<skill-dir>/scripts/catalog.py" search "随机" --cases --record-type evidence_event --case-domain clinical_research --limit 5
python "<skill-dir>/scripts/catalog.py" show C011
python "<skill-dir>/scripts/catalog.py" show C601
python "<skill-dir>/scripts/catalog.py" show R-CTG
python "<skill-dir>/scripts/catalog.py" stats
```

先选匹配的问题、机制与条件，再看完整案例。检索命中只是关键词匹配；命中数不表示证据强度。无结果时改用标题、机构、具体技术或模型编号，并查索引。

引用深度案例时查每项主张、历史行动缺口、观察结果与分析建议。引用事实事件时查其 `provenance.record_url`、快照 `record_key` 和字段定位；要讲决策或因果，继续打开完整官方记录。无法联网时明确缓存核验日期及尚未核查的后续变化。

## 覆盖与取样限制

当前样本集中在工程事故与故障、金融监管、临床研究和受认可的科学成果。它不是均衡的世界史，也不是各领域成功率、倒闭率、违法率或研究效果的代表样本。FDIC 与 CFPB 按可得年份分配记录；临床条目来自符合条件的 API 遍历；诺贝尔奖按三个科学类别各选 50 个年度奖项。这些选择不能用于总体统计推断。

当前 37 个模型有案例映射，63 个暂无映射。模型映射只是分析连接；不为填满 100 个模型而硬配案例。扩库优先解决用户问题中的机制、反例、领域和证据缺口，保留来源未报告的事实。获奖条目没有预装菲尔兹奖案例；按需研究流程见 [awards.md](awards.md)。

同一事件的不同报告、来源或模型视角共享事件身份，不计为新案例。一个机构的多个条目和不同来源组都不等于独立重复实验。
