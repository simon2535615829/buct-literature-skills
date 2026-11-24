---
name: translate-paper
description: 翻译整篇或指定范围的学术文献，按段交付双语对照、术语表和数字公式引文核验记录。
---

# 科研文献双语对照与保真核验

术语表允许用 source_forms 列出原文中的实际词形（如复数和过去式）。先对照本段的原文拼写，再检查目标术语；把确实未出现的术语留在本段的 terms 之外。


先读通研究问题、核心术语和结论的适用范围。用目标读者熟悉的术语翻译，按原文章节顺序覆盖标题、正文、表头、题注和脚注。跨页续段归到一个段号，保留两页定位；引用原文中的公式和符号可逐字复制。

1. 先冻结原文清单 source_blocks，每段登记 id、locator、text。长文以章节分批，带入前一段末句用于消解代词；上下文句不重复输出。遇到疑似串栏先对照原页。
2. 从定义句和首次出现处建立 glossary。每项保存原词、目标译名与采用依据；同形异义按语境分开，将适用的术语键列入本段 terms。缩写首次出现与原文对齐。
3. 为每个段号独立生成 translations。检查谁对谁做了什么、比较对象、否定范围、概率与限定词。例如 “did not demonstrate an increase” 表示尚未证实增加，不能译成“证实没有增加”。术语难定时保留原词并记录待确认项。
4. 脚本顺着原文顺序生成 bilingual.md 和 alignment.json，找出遗漏、重复映射、保护项和术语漂移。数字检查只负责提示，单位换算、公式语义与汉字数字须回到原文核验。末轮从结果句反向释义并核对原主张。

校验表会标出不等号、带分母的单位和测量值变化。若译者做了等价单位换算，在对照表补上原值、换算式和定位。逐项核对比较对象与数值的对应，即使数值集合完全相同也可能译反。

### 从实际文件建立原文索引

在表格、图注和多组实验的结果段中，先登记对象的双语对应关系。例如在段内设置 `"subject_pairs":{"site A":"甲站","site B":"乙站"}`。把两个站点的数值、单位、否定和不确定性分别回译核对。工具能对齐带明确对象的分句，允许分句换序；一个分句列出多个对象、出现代词或使用 respectively 时，需看原句和表头确认归属。检查结果与段号一起写入 review.json。

glossary 中的一般术语自动用于标题、题注和正文。遇到一词多义，用独立键登记 `{"source":"cell","target":"单元格","context_only":true}`，并把该键放入适用段的 terms。回读每项提示，对等价单位换算或合理的意译写明理由；词形检查无法判定整句语义。

在工作目录执行 `python /skills/weekly-skill/scripts/prepare.py 案例ID 索引目录 原始文件 [其他文件 ...]`。支持 UTF-8 文本、Markdown、逐行配置与 DOCX 正文段落和表格；原生文字 PDF 可选用 pypdf（Python 包），没有时用评测环境已有 PDF 阅读器转录。生成的 source.txt 和 inventory.json 保留原文块、来源位置、文件指纹和引文行号。把本题中间 JSON 与 source.txt 放在同一目录，按需选用 evidence 或 source_blocks。PDF 多栏、扫描页、Word 合并单元格、页眉脚注和公式须对照原件；索引只帮助定位。

## 在评测环境中使用

读取 /input/case.json、task.md、output_contract 和实际附件。记录 case_id、任务语言、受众、指定格式与证据范围。把下面示例中的字段换成当前案例的实际材料。先在 /app/work 处理，最终把成稿、必要的可编辑附件和 /app/output/result.json 放入 /app/output。保留原 output_contract 的字段名、类型与 case_id，将主结果、来源、修改记录、未解问题和状态填入相应字段。review.json 是本地机械检查的报告；语义判断、任务覆盖及正式结果须由执行 Agent 完成。材料缺失时交付可核查部分，标明缺失处。若案例要求 Office 或图形产物，生成指定格式，并打开实际渲染的 PDF/PNG 预览检查。

## 最小调用示例

最终成稿可先写成 /app/work/draft.json，将所需独立产物写到 /app/output，再运行 `python scripts/finish.py /input/case.json /app/work/draft.json /app/output`。用 `--artifact 文件名` 逐个检查附带的真实成品。它检验 case_id 和顶层必需字段并原子写入 result.json；若字段来自文字合同，用 `--require 字段名` 指明。字段类型、嵌套结构与科学内容仍要按案例核对。

从本 Skill 根目录运行下列命令，或将 scripts/run.py 替换为安装目录 /skills/weekly-skill 下对应的绝对路径。辅助脚本使用 Python 3.9 或更高版本及标准库。输入、引文与样例数据均为自建示例。

```sh
python scripts/run.py examples/input.json sample-output
```

示例在 bilingual.md 的 p1 同时保留上下限关系、2 mm 和引文 [3]。有复核项时阅读 review.json，修正实际发现的问题后选新的输出目录重跑；脚本遇到输入格式错误会退出并说明位置。

## 数值复核

在段落和给定的实验组内独立核对同量纲数值，包含浓度的分子、分母和不等号。允许明确等价的单位换算，如 1 mg/mL 对应 1 g/L；对象对调、上下界改变和数值漂移仍需复核。公式和引用保留字面形式；不支持的单位、复杂推导及译文质量由执行者对照原文复核。

时间单位按秒核对，包括 h、min、s、ms、µs 和 ns。组别、误差和界限仍逐项核验。

## 可复用教学示例与核验

图题、表头与正文使用独立段号。跨页续段保留两端定位并检查限定语的作用域。随包示例含正文、表头和带公式的图题；比较 alignment.json 的段号、保护标记与原句。

[查看教学示例的实际输出节选](examples/output-example.md)。
