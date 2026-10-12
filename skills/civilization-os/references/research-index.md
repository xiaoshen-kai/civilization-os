# 获奖研究索引

本库有 16 张代表性获奖研究卡：8 项经济学、4 项科学和 4 项菲尔兹相关数学研究，包含 42 条卡内来源记录与 54 条主张。它们独立于 100 个模型和 1000 条案例，既有 150 条诺贝尔事件仍只支持授奖事实；不是历届大奖成果全集。

每张卡有原问题、原理或定理、实际读取的版本与章节、成立前提、限制、误用、使用步骤和教学例子。应用状态说明迁移距离，不是效果评分；来源记录数不等于独立研究数。使用方式见 [awards.md](awards.md) 。

## 经济学研究

完整卡片在 [award-research-economics.json](award-research-economics.json)，按 ID 定位或运行 `show`。

| ID | 研究 | 年份 | 用途 | 模型导航 |
| --- | --- | ---: | --- | --- |
| A001 | 前景理论：参照点、损失厌恶与决策权重 | 2002 | 需核对条件 | P038、P039、P036 |
| A002 | 心理账户：预算分类、收入标签与整体取舍 | 2017 | 需核对条件 | P051、P052、P049 |
| A003 | 纳什均衡：相互回应与单方改变的边界 | 1994 | 需核对条件 | P009、P076 |
| A004 | 共同资源治理：参与规则、监督与冲突解决 | 2009 | 需核对条件 | P033、P040、P079、P082 |
| A005 | 有限理性与满意解：先定底线，再有限搜索 | 1978 | 需核对条件 | P028、P007、P058 |
| A006 | 柠檬市场：隐藏质量、逆向选择与可验证保障 | 2001 | 需核对条件 | P077 |
| A007 | 信号传递：可观察证据与模仿成本 | 2001 | 需核对条件 | P077、P040 |
| A008 | 延迟接受算法：稳定匹配与提议方的优势 | 2012 | 需核对条件 | P007、P009 |

## 科学研究

完整卡片在 [award-research-science.json](award-research-science.json)，按 ID 定位或运行 `show`。

| ID | 研究 | 年份 | 用途 | 模型导航 |
| --- | --- | ---: | --- | --- |
| A009 | 昼夜节律的转录与翻译反馈机制 | 2017 | 需核对条件 | P023、P026、P098 |
| A010 | 幽门螺杆菌与溃疡：从观察关联到病因证据 | 2005 | 知识学习 | P050、P098 |
| A011 | 准晶：长程有序不必等于平移周期性 | 2011 | 知识学习 | P098、P099 |
| A012 | Manabe 气候模型：机制、反馈与模型条件 | 2021 | 知识学习 | P016、P026、P098 |

## 菲尔兹相关数学研究

完整卡片在 [award-research-fields.json](award-research-fields.json)，按 ID 定位或运行 `show`。

| ID | 研究 | 年份 | 用途 | 模型导航 |
| --- | --- | ---: | --- | --- |
| A013 | Villani：最优运输、熵与非线性 Landau 阻尼 | 2010 | 知识学习 | P003、P004、P007、P098 |
| A014 | Green--Tao：质数中的任意长等差数列 | 2006 | 知识学习 | P002、P004、P098 |
| A015 | Mirzakhani：双曲曲面上的简单闭测地线计数 | 2014 | 知识学习 | P003、P010、P098 |
| A016 | Huh 与合作者：拟阵的 Hodge 理论与对数凹性 | 2022 | 知识学习 | P001、P008、P098 |

## 查找与读取

路径相对于本 Skill。将 `<skill-dir>` 换为实际绝对路径：

```text
python "<skill-dir>/scripts/catalog.py" search "心理账户" --research
python "<skill-dir>/scripts/catalog.py" search "奥斯特罗姆" --research
python "<skill-dir>/scripts/catalog.py" search "陶哲轩" --research --application learning_only
python "<skill-dir>/scripts/catalog.py" show A002
python "<skill-dir>/scripts/catalog.py" show AS-A002-2
```

`--research` 使用关键词匹配；主题、中文姓名或英文姓名均可尝试。`--model` 按关联 P 编号筛选，`--application` 筛选应用状态。模型检索结果的 `research_card_ids` 也提供入口。无结果不代表问题无法分析；可以换词、读索引或按需查证。

## 读完后能推出什么

先读 research 与 sources，核对 claims 的卡内来源，再看 decision_application 的条件、步骤与边界。`transfer_note` 明确哪些是本项目分析。授奖常表彰整体贡献，所选论文不等于全部获奖成果；合作者也不自动都是获奖者。

目前 9 张为条件分析、7 张为知识学习；四张菲尔兹卡均为学习用途。生活应用与例子没有个人效果实验，数学卡未完整审计全部证明。研究不适用时回到人的真实价值、约束和证据，不强行套用。

扩充与修订见 [maintenance.md](maintenance.md#获奖研究卡) 。
