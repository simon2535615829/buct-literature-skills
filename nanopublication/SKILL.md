---
name: nanopublication
description: 将论文主张拆为原子断言，绑定证据、版本、限定条件，导出 JSON 和可解析的 RDF N-Quads 命名图。
---

# 把论文结论拆成带证据的纳米出版记录

逐段标注观察者、主语、关系、对象、条件、否定和模态。一句话若同时报告两个独立比较，拆成两条；样本、温度、时间等限定留在同一条内。把作者报告、引文转述、间接推断分别建模。被否定的关系用负极性表达，避免产生一条无条件的正向事实。

1. 为资料登记元数据 documents 和证据 evidence（字段见示例）。保留论文题名、版本、可用标识、作者与年份；未知字段用 null，并解释。PDF 引文先形成按页的文本转录，用 locator 指回原论文；表格用行名、列名、单位定位。
2. 每条 claim 给出标准化但忠实的 subject、relation、object、condition、polarity、modality、confidence_basis。验证证据足以推出整个断言，若跨越两表或两个句子就同时绑定证据。间接推断应说明推导，冲突的结果分别保留并回查。
3. 脚本检查引文位置、断言字段、来源 ID，并用内容生成稳定局部 IRI。每条输出 Head、Assertion、Provenance 和 PublicationInfo 四张命名图。用带限定的陈述节点表达断言；本地词汇为 urn:paper-skill:，可按案例映射到指定本体。产物是本地 RDF 数据集；如要求可信 URI、签名或注册，应单独验证这些要求。
4. 重新解析导出，抽查主体和关系方向、文献版本与最小引文。全程区分论文作者和制作这条知识记录的 Agent。

发布者 creator 进入出版记录标识。相同证据集合换序或重复引用，生成相同标识。多个独立断言各自保留证据，回查导出中的 creator 和原作者可区分整理与研究工作的归属。

### 从实际文件建立原文索引

每条候选先对照原句，判定 support。直接观察填 direct；从多项观察得出的解释填 inferred，并在 derivation 交代前提、推导和适用条件；只有部分支撑或原文缺失填 partial 或 insufficient，reason 写清缺哪一段证据。旧输入未填 support 时沿用 direct，新提取的候选应逐项判定。原文同时支持互相矛盾的观察时，分别记录各自条件和来源。

比较、否定和跨表断言宜提供 bindings，按 subject、relation、object、condition 四个字段各填一个证据 ID 和最短原文片段，例如 `"condition":{"evidence":"E","text":"20 °C"}`。校验器核对片段出自本条已引用的证据。关系方向和片段能否推出整个断言仍由阅读论文的 Agent 核实。claims.json 与 nanopubs.nq 收录可导出的记录；pending.json 保留待核候选和原因，以便回到原文补证后重跑。来源转录本身损坏时先修复索引。

在工作目录执行 `python /skills/weekly-skill/scripts/prepare.py 案例ID 索引目录 原始文件 [其他文件 ...]`。支持 UTF-8 文本、Markdown、逐行配置与 DOCX 正文段落和表格；原生文字 PDF 可选用 pypdf（Python 包），没有时用评测环境已有 PDF 阅读器转录。生成的 source.txt 和 inventory.json 保留原文块、来源位置、文件指纹和引文行号。把本题中间 JSON 与 source.txt 放在同一目录，按需选用 evidence 或 source_blocks。PDF 多栏、扫描页、Word 合并单元格、页眉脚注和公式须对照原件；索引只帮助定位。

## 在评测环境中使用

读取 /input/case.json、task.md、output_contract 和实际附件。记录 case_id、任务语言、受众、指定格式与证据范围。把下面示例中的字段换成当前案例的实际材料。先在 /app/work 处理，最终把成稿、必要的可编辑附件和 /app/output/result.json 放入 /app/output。保留原 output_contract 的字段名、类型与 case_id，将主结果、来源、修改记录、未解问题和状态填入相应字段。review.json 是本地机械检查的报告；语义判断、任务覆盖及正式结果须由执行 Agent 完成。材料缺失时交付可核查部分，标明缺失处。若案例要求 Office 或图形产物，生成指定格式，并打开实际渲染的 PDF/PNG 预览检查。

## 最小调用示例

最终成稿可先写成 /app/work/draft.json，将所需独立产物写到 /app/output，再运行 `python scripts/finish.py /input/case.json /app/work/draft.json /app/output`。用 `--artifact 文件名` 逐个检查附带的真实成品。它检验 case_id 和顶层必需字段并原子写入 result.json；若字段来自文字合同，用 `--require 字段名` 指明。字段类型、嵌套结构与科学内容仍要按案例核对。

从本 Skill 根目录运行下列命令，或将 scripts/run.py 替换为安装目录 /skills/weekly-skill 下对应的绝对路径。辅助脚本使用 Python 3.9 或更高版本及标准库。输入、引文与样例数据均为自建示例。

```sh
python scripts/run.py examples/input.json sample-output
```

示例导出一个包含温度条件的比较及四个 RDF 命名图，缺失的作者、年份保留为空。有复核项时阅读 review.json，修正实际发现的问题后选新的输出目录重跑；脚本遇到输入格式错误会退出并说明位置。

## 核对比较方向

把双方、比较指标、条件、极性同直接引文逐项核对。调换比较双方时同时翻转大小关系。只有方向可唯一确认时才发布直接比较；否定、多义、相互冲突及复杂比较进入 pending.json，核实后重跑。推断记录另写推导过程。

直接断言须由同一条件下的观测原句支持。温度按数值和单位匹配，其他明确条件使用原文措辞；复杂跨句条件应人工核对后拆为独立观测。结果中的 supporting_clauses 和来源图保留匹配片段、证据 ID 及定位。同条件相反结果或条件含混时进入 pending.json。间接推论单列推导依据。

## 可复用教学示例与核验

examples/catalog/input.json 与同目录 source.txt 提供 20 条自建教学断言。五种观测量、成对仪器、温度与比较方向均需核对。运行 python scripts/run.py examples/catalog/input.json /tmp/nano-catalog，检查 claims.json 中每条记录的唯一 iri、sources、condition 和 confidence_basis，同时查看 pending.json。

[查看教学示例的实际输出节选](examples/output-example.md)。
