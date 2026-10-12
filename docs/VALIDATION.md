# 验收记录

核查时间：2026-10-12 15:20（北京时间）。本报告对应 100 个模型、100 个深度案例、900 个事实事件、213 条来源记录和 2100 条主张。

## 2.0.1 公开仓库准备

2026-10-12 15:38（北京时间）：完整 58 项回归全部通过，分别为目录 29 项、事件 15 项、发布 14 项。整库引用、900 条事件、模型反向索引和清单检查通过。新增发布检查覆盖 MIT 与第三方声明的必需副本和字节一致性。

公开内容独立审阅未发现私人路径、原始聊天、凭据或个体临床信息；源码包与独立 Skill 包的复制目录说明已分别修正。README 增加 GEO／产品验证示例、获取与安装方式；原创内容采用 MIT，第三方材料保留原权利边界。

仓库新增 .gitattributes 保留文件字节，避免 Git 自动转换行尾后破坏来源快照的 SHA-256。实际远端同步和全新克隆结果在完成后补充。

## 2.0.0 数据与行为基线

## 已完成检查

| 对象 | 方式 | 结果 |
| --- | --- | --- |
| 完整目录 | catalog.py validate；稳定 ID、引用、事件身份、主张 ID、来源组与清单 | 通过，0 个错误 |
| 模型反向索引与版本清单 | update_library.py 默认只读检查 | 一致 |
| 900 条派生事件 | event_records.py 默认只读比对 | 与最小字段快照一致 |
| 事件证据元数据 | verify_events.py；四类字段、哈希、完整派生字典、路径和重复检查 | 通过，900 条 |
| Skill 格式 | skill-creator 官方 quick_validate.py，建设端本地校验依赖 | 通过 |
| 标准库回归 | unittest discover | 56 项全部通过：目录 29 项、事件 15 项、发布 12 项 |
| 深度卡可执行性 | 检查 100 条 decision_review | 均含当前检验、指标、停止条件和分析建议身份 |
| NASA 来源定位 | 主维护流程重放 50 条来源的三字段行定位及 SHA-256 | 150 个定位一致 |
| 新增事实字段 | 对实际取得的原始 API 或 HTML 单独重放 | 300 FDIC、200 CFPB、250 Clinical、150 Nobel 均一致 |

原始上游重放与发布包内一致性是两种检查。前者实际取得 FDIC JSON、CFPB 目录 HTML、ClinicalTrials.gov 四页完整响应和 Nobel 官方 API 响应，再核对精选字段；后者可由用户在离线包内复现。原始研究缓存没有打包。

Clinical 的 80 条 ESTIMATED 首次结果公开日期保留原值；250 条结果另保留离散类型、分析单位和选定分母单位。未知字段为 null，不补造值。Nobel 获奖年度与授奖日期可以跨年，未强制改成同一年。

## 限定场景审阅

| 问题 | 实际定位 | 行为结论 |
| --- | --- | --- |
| GEO 服务转 SaaS，现金约束未知 | P058、P065、P094 | 条件建议、先验证真实付款；没有编平台能力或要求裸辞 |
| 目录能否证明违法与罚款已付 | C401、C402、C403 | 保留立案、指控、认定、义务与支付的区别 |
| NCT00934102 哪款更好 | C602 | 保留 ESTIMATED 和结果单位，没有从几项均值给医疗优劣结论 |
| 两句话讲贝叶斯 | P005 | 简短教学，示例计算为 2/3 |
| 离线查询 2026 年最新诺贝尔 | C1000 与无命中的 2026 查询 | 未把 2025 缓存当作最新，也未把无命中当成未颁奖 |
| 备份误删复盘 | C091 | 区分实际恢复、后续计划与当前隔离演练建议 |
| 历史近失但动作未知 | C011 | 未补造执行；作者建议与历史行动分开 |

独立审阅发现临床结果初稿保留 spread 而缺少其类型，已根据实际原始字段补齐并重新生成、重放与回归。审阅者复读 C602 确认 Standard Deviation、Eyes 和 Participants 保留。此审阅基于明确的有限缓存场景，不是自动端到端产品评测或预测准确率测量。

## 发布检查

发布工具的 12 项回归覆盖两次构建字节一致、固定元数据、成员逐字节核对、版本取值、路径范围、敏感内容拒绝、默认不覆盖，以及 Git 元数据与缓存的只读排除。

正式构建使用同一工具逐成员比较仓库包和 Skill 包，SHA-256 写入包外的 checksums.txt。两包分别以 civilization-os-repo/ 和 civilization-os/ 为根；原始聊天、工作资料、个人配置、依赖和缓存不属于交付。

## 复现

从仓库根运行：

```text
python -X utf8 skills/civilization-os/scripts/catalog.py validate
python -X utf8 skills/civilization-os/scripts/event_records.py
python -X utf8 skills/civilization-os/scripts/verify_events.py
python -X utf8 scripts/update_library.py
python -X utf8 -m unittest discover -s tests
python -X utf8 scripts/build_release.py --output-dir ../civilization-os-release
```

离线校验不能独立证明源头事实、当前法律状态、完整研究质量或因果机制。案例覆盖也不是均衡历史样本：37 个模型有案例关联，63 个暂未关联。完整源头与数据边界见 [DATA.md](DATA.md) ，发布步骤见 [GITHUB.md](GITHUB.md) 。原创代码与文档现采用 MIT；第三方资料仍按 DATA.md 和 NOTICE.md 处理。
