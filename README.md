# Civilization OS

**把商业、产品、职业与学习问题，转化为可核验的判断、可比较的选项和可执行的下一步。**

Civilization OS 是一套可在 Codex 与 Claude Code 中使用的跨学科决策 Skill。它把 100 个模型卡片、100 个深度案例和 900 个事实事件连接到一个工作流：明确问题，选取少量模型，核查证据，比较路径，设计试验，再根据结果更新判断。

## 适合用来做什么

| 问题 | 主要输出 |
| --- | --- |
| 产品定位、GEO、商业模式与资源投入 | 客户任务、关键假设、选项比较、指标与验证计划 |
| 职业选择、学习投入与个人战略 | 成立条件、机会成本、能力缺口与可逆的第一步 |
| 理解跨学科模型与科研成果 | 概念、机制、例子、反例与适用边界 |
| 项目、组织与决策复盘 | 当时的信息、事实与解释的区分、可验证的流程改进 |
| 核查案例或为方案寻找依据 | 有出处的有限主张、迁移条件与仍需补充的证据 |

一次分析通常选用 2 至 4 个互补模型，交付当前建议、决定性证据、改变建议的条件和第一步。信息不足时保留条件结论；简单问题无需走完整流程。

## 知识库包含什么

| 内容 | 数量 | 记录范围 |
| --- | ---: | --- |
| 模型卡片 `P001-P100` | 100 | 机制、所需输入、适用条件、限制、误用与出处 |
| 深度案例 `deep_case` | 100 | 决策背景、记录的动作和结果、主张定位、当前检验与迁移边界 |
| 事实事件 `evidence_event` | 900 | 可定位的有限事实与精选原始字段快照 |

深度案例包括 10 个既有种子案例、50 个 NASA LLIS 经验复盘、30 个 CFPB 执法复盘和 10 个技术案例。事实事件包括 300 个 FDIC 银行失败记录、200 个 CFPB 执法目录事件、250 个 ClinicalTrials.gov 临床结果记录和 150 个诺贝尔科研授奖记录。

**1000 条记录包含两种深度，不是 1000 个完整决策复盘。** 深度案例的格式也不等于完整历史重建；事实事件不提供因果结论。模型映射是本仓库的分析，不能据此认定当事人实际使用了该模型。当前案例关联 37 个模型，另有 63 个模型暂无本地案例关联；目录规模不表示准确率或均衡覆盖。

**本包是历史学习快照，资料核查日期为 2026-10-12，事件筛选截止为 2025-12-31；不反映 NLM 或其他来源当前最新、最准确的数据。** 当前平台能力、政策、产品或市场事实须重新核查。覆盖、取样、来源与许可边界见 [DATA.md](docs/DATA.md) 。

## 快速开始

### 1. 获取文件

在 GitHub 仓库页面选择 `Code` → `Download ZIP`，解压后找到 `skills/civilization-os/`。也可以使用 Git 获取源码：

```text
git clone https://github.com/xiaoshen-kai/civilization-os.git
cd civilization-os
```

源码下载方式见 [GitHub 官方文档](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives) 。根据文件来源，选择需要复制的目录：

| 文件来源 | 解压后需要复制的目录 |
| --- | --- |
| GitHub 源码 ZIP、Git 克隆或完整仓库 ZIP | 仓库内部的 `skills/civilization-os/` |
| 本地构建的独立 Skill ZIP | 压缩包根目录的 `civilization-os/` |

### 2. 手工安装

将上表中对应的目录完整复制到以下任一位置，目标目录名保持为 `civilization-os`，保留 LICENSE、NOTICE.md、`SKILL.md`、`references/`、`scripts/` 和 `agents/` 的相对结构：

| 工具 | 仅当前项目 | 个人所有项目 |
| --- | --- | --- |
| Codex | `.agents/skills/civilization-os/` | `~/.agents/skills/civilization-os/` |
| Claude Code | `.claude/skills/civilization-os/` | `~/.claude/skills/civilization-os/` |

`~` 表示用户主目录。项目安装位置属于使用该 Skill 的目标项目；本仓库的 `skills/` 是分发目录。同名目录已存在时，先比较版本并保留需要的本地改动，再选择替换。Codex 未显示新 Skill 时可重启会话。路径依据 [OpenAI 官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills) 与 [Claude Code 官方 Skill 文档](https://code.claude.com/docs/en/skills) 。

手工复制不需要 API Key、MCP 服务或额外 Python 包。没有 Python 时，仍可直接读取 [Skill 入口](skills/civilization-os/SKILL.md) 与 `references/`；脚本用于检索和一致性检查。

### 3. 提出一个具体问题

在 Codex 中用 `$civilization-os`，在 Claude Code 中用 `/civilization-os` 显式调用，也可以说“使用 Civilization OS”或“文明模式”。把决定、选项、时间窗和约束一起交给模型。

下面是可直接修改的 GEO 与产品分析示例，其中时间和资源为教学设定：

```text
使用 Civilization OS，帮我为一家 B2B SaaS 制定 GEO 与产品定位验证计划。

目标：4 周内判断，哪种内容投入更能帮助目标客户理解和选择产品。
资源：2 人，合计最多 40 小时。
选项 A：完善产品说明、适用场景与可核验的证据页面。
选项 B：扩充行业知识内容。
已有材料：产品介绍、目标客户任务、10 个真实客户问题、现有流量与咨询记录。
如果材料不足，请先指出最可能改变选择的信息，再在明确假设下继续。

请选取 2 至 4 个互补模型，区分事实、假设与本次模型映射。
先核查涉及平台当前能力的官方资料；历史案例说明可迁移与不可迁移的条件。
输出选项比较、最小验证试验和一张行动表，包含负责人、投入上限、
数据采集方式、基线、观察指标、停止条件与复盘时间。
引用、有效咨询和产品选择分别记录，不用单个指标代替业务结果。
```

执行时先补齐示例中的实际材料，记录基线与采集条件，再比较试验结果。模型帮助确定变量与验证方法；效果需要真实数据检验。

复盘也可以从一个短请求开始：

```text
文明模式：帮我复盘一个延期项目。先区分当时可知的信息与事后信息，
检索相关深度案例，说明迁移条件，最后给出可验证的流程改进。
```

## 离线检索

脚本使用 Python 3.10 或以上版本的标准库。以下命令从仓库根执行；系统使用 `python3` 时，将 `python` 替换为 `python3`。

```text
python -X utf8 skills/civilization-os/scripts/catalog.py stats
python -X utf8 skills/civilization-os/scripts/catalog.py search "机会成本 复利"
python -X utf8 skills/civilization-os/scripts/catalog.py show P058 --format md
python -X utf8 skills/civilization-os/scripts/catalog.py search "退款" --cases --record-type deep_case --case-domain business --limit 5
python -X utf8 skills/civilization-os/scripts/catalog.py search "随机" --cases --record-type evidence_event --model P050 --case-domain clinical_research --limit 5
python -X utf8 skills/civilization-os/scripts/catalog.py show C061
```

`--cases` 切换到案例检索，`--record-type` 选择层级，`--model` 按模型 ID 过滤，`--case-domain` 按案例领域的精确字符串过滤。用 `stats` 查看实际领域，或直接读 [模型索引](skills/civilization-os/references/model-index.md) 与 [案例索引](skills/civilization-os/references/case-index.md) 。

这是关键词检索；无结果时换关键词或读索引，不能据此断言没有合适模型或证据。安装后运行脚本时，将命令中的 `skills/civilization-os/` 替换为实际 Skill 路径；数据路径由脚本自身位置确定。

## 检查与本地打包

```text
python -X utf8 skills/civilization-os/scripts/catalog.py validate
python -X utf8 skills/civilization-os/scripts/verify_events.py
python -X utf8 -m unittest discover -s tests
python -X utf8 scripts/build_release.py --output-dir ../civilization-os-release
```

`validate` 检查结构、唯一 ID、引用、模型关联与证据元数据；`verify_events.py` 对照包内字段快照、主张定位与摘要。这些离线检查不访问实时网站，不能替代历史事实、完整原文或因果关系的人工核验。实际验收与局限见 [VALIDATION.md](docs/VALIDATION.md) 。

构建器在仓库外生成完整仓库 ZIP、可单独安装的 Skill ZIP 和 `checksums.txt`，文件名包含 `manifest.json` 中的版本。相同文件内容产生相同 ZIP 字节，默认不覆盖已有结果。Git 元数据、测试缓存、依赖和构建产物被排除；发现工作资料、环境配置、个人配置或常见秘密时拒绝打包。

## 源码与维护入口

```text
skills/civilization-os/
  SKILL.md               触发说明、分析流程与边界
  references/            模型、两层案例、来源与知识说明
    event-data/          事实事件的精选字段快照
  scripts/               只读检索与离线验证
  agents/                Codex 展示元数据
scripts/                 可复现发布包构建器
tests/                   离线回归检查
docs/                    数据、验收与上传说明
```

| 文档 | 内容 |
| --- | --- |
| [DATA.md](docs/DATA.md) | 来源、选择规则、历史时间与权利边界 |
| [VALIDATION.md](docs/VALIDATION.md) | 实际验证方式、结果与未覆盖范围 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 稳定 ID、主张定位与贡献流程 |
| [AGENTS.md](AGENTS.md) | 仓库维护规范 |
| [ROADMAP.md](ROADMAP.md) | 当前建设与验证状态 |
| [GITHUB.md](docs/GITHUB.md) | GitHub 上传与发布准备 |

## 许可

本仓库的原创代码与原创文档采用 [MIT 许可证](LICENSE) 。第三方来源、精选原始数据字段和商标继续适用各自的许可与使用条件，详见 [NOTICE.md](NOTICE.md) 与 [DATA.md](docs/DATA.md) 。MIT 不重新授权临床申报材料、诺贝尔机构商标或其他第三方内容；某个来源属于 CC0 或公共领域，也不代表所有来源拥有相同权利。
