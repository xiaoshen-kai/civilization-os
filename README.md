# Civilization OS

**帮助普通人面对一生中各类选择：看清自己在乎什么，理解现实条件，比较可能的路径，作出属于自己的决定。**

Civilization OS 是一套可在 Codex 与 Claude Code 中使用的跨学科决策与学习 Skill。用途不限职业、行业或固定场景；从买一件东西、安排时间，到选择居住地、处理关系、转换职业或寻找人生方向，都可以从正在经历的困惑开始。

它把 100 个模型卡片、100 个深度案例和 900 个事实事件连接到一个工作流：明确问题与个人价值，选取适合的模型，核查必要证据，比较路径，再确定下一步与重新考虑的条件。收入、效率、稳定、亲密关系、自由或意义的权重由使用者决定，Skill 不替你规定怎样的人生更好。

## 可以从哪些问题开始

以下只是使用示例，任何未列出的决定也可以提出；职业与商业同样属于可用领域。

| 问题示例 | 可以帮助整理什么 |
| --- | --- |
| 日常消费、时间安排与生活习惯 | 实际需要、预算、取舍、替代选择与容易忽略的成本 |
| 人生方向、居住地与生活方式 | 在乎的生活、现实约束、可考虑的路径与长期影响 |
| 伴侣、家庭、朋友与照护安排 | 各方需要、价值冲突、边界与可以沟通的下一步 |
| 职业选择、学习投入与个人成长 | 动机、机会成本、能力缺口、选项与重新考虑的条件 |
| 健康、财务等重要决定 | 事实、偏好、风险、待核实信息与需要向专业人士提出的问题 |
| 创业、产品与组织决策 | 目标、关键假设、资源取舍、证据与适合的验证方式 |
| 理解模型、科研成果与复盘经历 | 概念、机制、反例、当时的信息与可以借鉴的经验 |

简单问题可以直接给出简短判断；复杂问题通常选用 2 至 4 个互补模型。没有清楚的选项或目标时，先帮助梳理，不要求先填完整表格。信息不足时给出有条件的判断；价值冲突时保留取舍与使用者的决定权。

下一步可以是收集信息、沟通、等待、采取行动，或在合适时做一次小范围尝试。关系、情感和人生意义无需强行量化，每个决定也不必设计试验。

## 知识库包含什么

| 内容 | 数量 | 记录范围 |
| --- | ---: | --- |
| 模型卡片 `P001-P100` | 100 | 机制、所需输入、适用条件、限制、误用与出处 |
| 深度案例 `deep_case` | 100 | 决策背景、记录的动作和结果、主张定位、当前检验与迁移边界 |
| 事实事件 `evidence_event` | 900 | 可定位的有限事实与精选原始字段快照 |

深度案例包括 10 个既有种子案例、50 个 NASA LLIS 经验复盘、30 个 CFPB 执法复盘和 10 个技术案例。事实事件包括 300 个 FDIC 银行失败记录、200 个 CFPB 执法目录事件、250 个 ClinicalTrials.gov 临床结果记录和 150 个诺贝尔科研授奖记录。

**1000 条记录包含两种深度，不是 1000 个完整决策复盘。** 深度案例的格式也不等于完整历史重建；事实事件不提供因果结论。模型映射是本仓库的分析，不能据此认定当事人实际使用了该模型。当前案例关联 37 个模型，另有 63 个模型暂无本地案例关联；目录规模不表示准确率或均衡覆盖。

当前本地案例偏向工程、监管、临床研究和科学奖项，这些是已有证据的覆盖范围，不是 Skill 的用途边界。遇到缺少同领域案例的人生问题，仍可先分析价值、选项与约束，再按需要查证资料；不把工程或商业案例硬套到个人生活。

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

### 3. 从你的困惑开始

在 Codex 中用 `$civilization-os`，在 Claude Code 中用 `/civilization-os` 显式调用，也可以说“使用 Civilization OS”或“文明模式”。可以只说一句困惑，也可以补充已知的情况；没有目标、选项或截止时间时，不必编造。

下面的通用模板可以直接修改。每一项都可选，只保留你愿意提供且与当前问题有关的内容：

```text
使用 Civilization OS，帮我想清楚这个决定：
[我正在犹豫什么，或我觉得哪里不对劲。]

如果有帮助，我目前知道的是：
- 我最在乎的事情，以及彼此冲突的愿望。
- 已经考虑的选择；也可能还不知道有哪些选择。
- 现实情况、必须守住的边界，以及愿意承受的代价。
- 是否需要尽快决定；也可能只是想先理清方向。

请先判断我需要的是梳理问题、比较选择，还是形成行动。
缺少关键的信息时，只问最能影响判断的问题，并说明可以先作哪些假设。
需要时区分事实、推断与价值取舍，说明建议成立和改变的条件。
用适合这个问题的深度回答，帮助我作自己的决定，并给一个合适的下一步。
```

生活中的问题可以很简短。以下是使用示例，不是案例库中的真实事件：

```text
文明模式：手机还能用，但我总想换新。我想分清这是实际需要，
还是一时冲动，帮我比较继续用、维修和换新的取舍。
```

```text
使用 Civilization OS：父母希望我回家乡，我喜欢现在的城市。
我既在乎陪伴，也在乎自己的生活，不知道还有哪些安排可以考虑。
先帮我理清冲突和可以沟通的内容，不用给关系打分。
```

```text
使用 Civilization OS：工作很稳定，但我越来越想学一门新技能。
我还没想好是否换职业，先帮我分清自己想改变什么，
哪些信息值得弄清，再决定接下来做什么。
```

模型和历史案例用于帮助看清问题与检查判断，实际选择仍取决于你的处境、价值和可接受的代价。

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
