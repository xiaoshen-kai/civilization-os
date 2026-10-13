# 贡献指南

本仓库接受能改善模型适用性、事实可追溯性、检索行为或使用体验的改动。先读取 [AGENTS.md](AGENTS.md) 和 [数据说明](docs/DATA.md) ，检查现有目录与 ID，避免重复事件和无依据的深度扩写。

本项目原创代码与原创文档采用 [MIT 许可证](LICENSE) ；第三方资料仍按 [NOTICE.md](NOTICE.md) 中的原许可与条件处理。提交者应有权提供自己的文字与代码，不把第三方全文或受限材料转交给仓库。

## 数据规则

- 模型使用稳定 ID `P001-P100`。保留现有 ID，修改机制或边界时同步来源与相关案例；定理、规律、理论、经验研究、启发式和争议假说不得互相替代。
- 获奖研究卡使用独立 A 编号，写入 `award-research-*.json`，卡内来源与主张分别使用 `AS-Axxx-n`、`Axxx-Kn`。精确记录奖项关系、所读原研究版本和范围；区分研究结论与分析者生活迁移，按实际用途标为 `direct`、`conditional` 或 `learning_only`。详细规则见 [研究卡维护](skills/civilization-os/references/maintenance.md#获奖研究卡) 。
- 案例保留 `record_type`。`deep_case` 写背景、记录的动作、结果、迁移条件和限制；`evidence_event` 写可定位事实。仅有目录元数据时，保持事实事件层级。
- 每个独立事件使用稳定 `event_key`。同一银行 API 行、NCT 研究、年度授奖类别或执法程序不能因多个结果、组别、当事人或附件拆成多条以增加数量。相关事件可交叉引用；共同的底层事件需按实际范围去重。
- 事实主张使用稳定 `claim_id`，例如 `C061.01`；主张关联已存在的 `source_ids` 与精确 `locator`。来源应指向实际打开过的完整网页、文件或结构化记录，不能把搜索摘要、目录链接或机构信誉当作完整原文核验。
- 模型关联应说明它帮助检查什么，不应声称当事人使用了该模型。事实支持和因果支持分别判断；`fact_confidence` 高不自动提高 `causal_confidence`。
- `origin_group` 标识信息的来源组。多个同机构文件、联合公告、转述或转载可能来自同一事实基础；`independent_source_groups` 不代表独立实验、复现次数或证据质量评分。
- 日期按来源保留精度；未知日期不猜。分别记录事件时间、来源发布日期和 `checked_on`；临床结果首次提交与首次公开日期、`ACTUAL` 与 `ESTIMATED` 不得混用。
- 执法材料区分指控、机构认定、同意令、法院裁决与后续撤销。被要求付款不等于已经付款，被要求整改不等于整改完成；只有新的明确依据才能升级表述。

所有扩充须遵守实际数据源的许可与使用条件。保留必要归属，不复制版权人物的长段原文，不使用机构徽标或暗示背书。临床材料不包含联系人信息、个体参与者数据或整份研究文本。

## 文件入口

| 修改对象 | 位置 |
| --- | --- |
| 工作流与触发说明 | `skills/civilization-os/SKILL.md` |
| 模型卡片 | `skills/civilization-os/references/models-*.json` |
| 获奖研究与卡内来源 | `skills/civilization-os/references/award-research-*.json`；导航为 `research-index.md` |
| 案例 | `skills/civilization-os/references/cases.json`、`cases-*.json` |
| 来源 | `skills/civilization-os/references/sources-*.json` |
| 事实事件字段快照 | `skills/civilization-os/references/event-data/` |
| 库版本与汇总 | `skills/civilization-os/references/manifest.json` |
| 检索与校验 | `skills/civilization-os/scripts/` |
| 回归检查与发布 | `tests/`、`scripts/build_release.py` |

公开快照只保存支撑主张所需的字段、选择规则、读取元数据与摘要；不要把工作区原始资料、聊天或本机安装目录复制到仓库。公开目录不得依赖未打包的研究缓存。新增根文件时同步构建白名单，确保构建产物包含需要的公开文件。根目录 LICENSE 与 NOTICE.md 为维护源，Skill 内副本保持字节一致。仓库用 .gitattributes 保留原始行尾字节，避免 Git 配置改变快照哈希；重新格式化快照时须同步派生记录并核验。

## 改动流程

1. 确定具体问题、允许改动范围和验证方式。修改数据前检查重复 `event_key`、已有来源与更正记录；不要顺手重排现有 ID。
2. 完成必要的一手核验，写出原始事实与本次解释之间的边界。无法读取正文时保留有限主张，待核验材料不能混入已核验库。
3. 修改对应文件；结构化数据使用 UTF-8，中文用全角标点并保留中英空格。命令、文件名、ID 和 URL 保持原样。
4. 更新真实受到影响的文档与 `manifest.json`；状态和待确认事项写入 `ROADMAP.md`，README 只描述实际实现。
5. 运行下列检查并查看结果。提交说明写明具体变化、事实出处、验证方式和剩余限制，不凭条数声称完成核验。

```text
python -X utf8 skills/civilization-os/scripts/catalog.py validate
python -X utf8 skills/civilization-os/scripts/verify_events.py
python -X utf8 -m unittest discover -s tests
```

涉及检索逻辑时，另检查真实场景：无结果、无效 ID、领域与层级过滤、只读行为，以及含有相似关键词但不应支持结论的案例。仅修改可逆、低影响文字时，不新增与实现机械对应的测试。

准备发布时，先完成检查，再运行本地构建：

```text
python -X utf8 scripts/build_release.py --output-dir ../civilization-os-release
```

如输出目录已有同名发布包，可选择另一个目录；明确需要重新生成时再使用 `--overwrite`。不要把 ZIP、缓存、凭据、真实环境配置或个人路径提交到源码树。提交、推送、创建 PR 和公开发布由维护者另行授权或手工执行。

## 报告错误

报告事实错误时提供案例或主张 ID、正确的一手来源、定位和需要改正的措辞。报告程序问题时提供执行命令、Python 版本、预期与实际结果；去掉个人路径和敏感信息。报告因果解释问题时说明混淆、选择偏差、缺失比较或迁移条件，不只说某个来源“权威”或“可靠”。

## 模型操作层贡献

在已有 P 卡内维护 `application`，保留核心原理、来源与案例身份。具体字段、用途状态、原创教学例和跨学科导航要求见 [maintenance.md](skills/civilization-os/references/maintenance.md#模型操作与学科导航) 。教学例与反例须标明原创情境，不计入历史案例；跨学科连接保留适用前提与还需查证的专业知识。
