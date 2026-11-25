---
name: write-related-work
description: 从指定论文与本研究材料编写背景、相关工作、研究空白和贡献，生成逐句引证映射与可编辑成稿。
---

# 由论断和证据编写引言与相关工作

Draft the four paragraphs in the requested language. Use examples/input.json as the input schema. For a complete draft set require_complete to true. Use the actual excerpts and their document IDs, and write a different sentence for each section.

Start with a source ledger in your working notes: for each prior author write down the approach, the tested condition and its excerpt; for the current paper record what was actually done, what is planned and what is unmeasured. Use the authors' names in the related paragraph when provided. Cite each author's own route next to that sentence. For the gap, cite all prior works whose scope you describe, and qualify it as a gap in those works. For the contribution use the current paper's own excerpt. If the gap link needs review, a factual statement about the current study can still be delivered: optionally set standalone_quote to an exact, self-contained sentence from a cited own-work excerpt. The script keeps that quotation separate from the unresolved claim that it closes the gap. Never suggest a ranking or completed outcome without comparable results.

| section | prose to write | fields on the claim |
|---|---|---|
| background | Introduce the concrete research question or task. | evidence from the supplied material |
| related | Attribute the specific method and observed scope to its authors. | prior evidence |
| gap | Explain which question that **particular prior study** leaves open. | evidence from the prior study, scope as a short description, scope_documents as a list of its document IDs |
| contribution | State what the current authors did or plan to do about that question. Preserve the status stated in the source. | own evidence, gap_id equal to the id of the gap claim |

For a requested synthesis of multiple routes, compare the tested boundaries before drafting the gap. If two sources each explicitly report the same limitation, include both in the gap citations and scope_documents. Set the optional top-level gap_review_documents to the prior works the case actually asks you to compare. For unrelated or undocumented limitations, keep separate, narrower claims and identify any missing evidence.

Build the gap from the prior study even when the current proposal names the new condition. If the new condition is mentioned only in the proposal, you may cite both sources to frame the question. A proposal supports future tense. Deliver when the four paragraphs in manuscript.md have distinct functions and their citations resolve. If the tool reports an incomplete draft, read the claim-level reasons, correct the links and sentences, and run again in a fresh directory. When the supplied documents genuinely lack evidence, keep the partial draft and identify the missing sources.

### 从实际文件建立原文索引

实际写作时先用一句话写清研究对象、任务和约束。每段相关工作围绕一个读者需要作出的比较，用主题句起段，随后引入两条路线各自的证据，再用一句话解释为何这种差异影响本文的问题。给同段各句相同的 paragraph。比较结论需要回读原文，例如，两篇论文各自在不同测试集上进步，只能分述各自结果。干预效果、相关性、计划中的实验要分别措辞。

对每个 comparison 行提供 work、路线、条件、evidence；需要量化排名时另外填写 dataset、split、metric、protocol。在相应 claim 填 comparison_works 和 comparison_kind（ranking 或 qualitative）。研究空白填 scope、scope_documents，逐篇记录限制的原文，区分论文明确排除一种场景和材料没有交代该场景。给每项贡献指定 gap_id，并引用本研究的图、表、方法或协议。只观察到计划就写“拟检验”，结果尚未测得时不可写成“已改善”。人工逐句核实含义，用 support=partial 或 uncertain 标出待收窄的句子；缺少证据时用空 evidence。工具把这些句子保存在 evidence-map.json，成稿采用通过检查的论断。查看其中的 reasons，补引、收窄或删句后重跑，直至成稿四部分衔接。最后按案例指定的文种、长度、章节和引文样式排版。

在工作目录执行 `python /skills/weekly-skill/scripts/prepare.py 案例ID 索引目录 原始文件 [其他文件 ...]`。支持 UTF-8 文本、Markdown、逐行配置与 DOCX 正文段落和表格；原生文字 PDF 可选用 pypdf（Python 包），没有时用评测环境已有 PDF 阅读器转录。生成的 source.txt 和 inventory.json 保留原文块、来源位置、文件指纹和引文行号。把本题中间 JSON 与 source.txt 放在同一目录，按需选用 evidence 或 source_blocks。PDF 多栏、扫描页、Word 合并单元格、页眉脚注和公式须对照原件；索引只帮助定位。

## 在评测环境中使用

读取 /input/case.json、task.md、output_contract 和实际附件。记录 case_id、任务语言、受众、指定格式与证据范围。把下面示例中的字段换成当前案例的实际材料。先在 /app/work 处理，最终把成稿、必要的可编辑附件和 /app/output/result.json 放入 /app/output。保留原 output_contract 的字段名、类型与 case_id，将主结果、来源、修改记录、未解问题和状态填入相应字段。review.json 是本地机械检查的报告；语义判断、任务覆盖及正式结果须由执行 Agent 完成。材料缺失时交付可核查部分，标明缺失处。若案例要求 Office 或图形产物，生成指定格式，并打开实际渲染的 PDF/PNG 预览检查。

## 最小调用示例

最终成稿可先写成 /app/work/draft.json，将所需独立产物写到 /app/output，再运行 `python scripts/finish.py /input/case.json /app/work/draft.json /app/output`。用 `--artifact 文件名` 逐个检查附带的真实成品。它检验 case_id 和顶层必需字段并原子写入 result.json；若字段来自文字合同，用 `--require 字段名` 指明。字段类型、嵌套结构与科学内容仍要按案例核对。

从本 Skill 根目录运行下列命令，或将 scripts/run.py 替换为安装目录 /skills/weekly-skill 下对应的绝对路径。辅助脚本使用 Python 3.9 或更高版本及标准库。输入、引文与样例数据均为自建示例。

```sh
python scripts/run.py examples/input.json sample-output
```

示例的 G1 限定于材料 A，C1 引用本文的 E2；最终稿附四部分和文献映射。有复核项时阅读 review.json，修正实际发现的问题后选新的输出目录重跑；脚本遇到输入格式错误会退出并说明位置。

## 引文缺失时的交付

证据编号或论文归属无法解析时，在 evidence-map.json 逐项保留请求的编号和原因，将受影响的论断从定稿中移出。无效对照行不得支持排名，缺口未证实时暂缓对应贡献。其余有证据的段落继续生成。核实原文后补齐索引，在新输出目录重跑。

单条证据文件缺失、引文不符或行号失效时，review.json 记录原因。正文保留有证据的段落，依据无效的研究空白及依赖它的贡献进入复核。


## 可复用教学示例与核验

examples/planned 用两份教学材料区分前人已经完成的研究与本研究尚未实施的计划。运行 python scripts/run.py examples/planned/input.json /tmp/intro-example，逐段核对前人证据、gap 的 scope_documents 和贡献的 gap_id。

[查看教学示例的实际输出节选](examples/output-example.md)。
