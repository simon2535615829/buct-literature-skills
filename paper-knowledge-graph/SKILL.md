---
name: paper-knowledge-graph
description: 按主题把多份文献转换为有方向和适用条件的图，支持出边、入边和两跳证据路径查询。
---

# 构建可查询、能回到原文的文献知识图谱

先用原文登记实体，再逐条检查候选边。收到未登记的端点时，原样保存候选边的 id、source、target，把它交给 rejected_edges 路径。不得为凑齐一条边而创建名为 unknown 或“未知”的替身节点，也不要将边 ID 改当节点 ID。只有当证据真的命名了新实体才能补入节点表；独立的有效边仍然可以参与查询。
When an input supplies a candidate edge with an unregistered endpoint, copy its original edge ID and endpoint IDs to the input edges list, without synthesizing a placeholder node. The graph builder can then isolate that edge and preserve legitimate paths.


先把用户的问题写成图查询：例如“谁测量指标 M”“方法 A 在给定条件下优于谁”“A 使用的仪器测量什么”。由问题限定节点类型、关系方向和抽取范围，避免把论文的一切名词都加入图中。

实体登记稳定 ID、类型、显示名、别名及证据。跨论文合并优先依赖实体标识或作者明示的同义关系；缩写、同姓和拼写接近只能生成候选。把判定依据写入 alignment_notes；同名异物保留不同 ID。新增论文时复用已核实 ID，新增边用新的稳定 ID，不覆盖先前结论。

每条边保存 source、target、predicate、condition、polarity 和 evidence。区分“用了”“评价了”“优于”“引用了”。共现不能推出因果，综述转述标明间接来源。对相反证据保留两条边及各自条件。在原始文本或逐页转录中核对引文，给 locator 填章节、页码或表格单元。

按案例实际问题填写 queries，支持 out、in、two_hop，条件和谓词可选。出边/入边返回一跳，两跳匹配指定两个谓词且保留每条边的证据。无匹配只说明当前资料覆盖有限。对至少三个有意义的问题给出答案、完整路径、最短充分证据和无法推定项。不要把两跳路径自动写成直接因果边。

当问题限制第二跳时填写 second_condition 或 second_polarity，第一跳使用 condition 和 polarity。只提供 second_predicate 时会返回匹配该谓词的全部第二跳，作答时保留每步条件。

### 从实际文件建立原文索引

在节点的 aliases 数组中只登记可回查的别名，例如 `["optical probe","光学探头"]`，在节点 evidence 中引用定义句。查询 start 可用稳定 ID、显示名或已登记别名。遇到同名会返回 candidates；先比较类型、论文和原文，再用明确的 ID 重查。未找到实体或路径时，把材料覆盖范围写进回答。跨文献的简称相似本身不足以合并节点。

读取 answers.json 的 evidence_paths，沿路径逐边给出关系方向、原句和 locator。正向筛选仍会在 conflicts 单列相同主体、谓词、客体和条件下的相反观察，并附两边原文。用 positive、negative 记录明确极性；归一化同义条件时保留温度、样本、时间窗等差别。不同条件下的结论可并存。两跳路径表示两条已记录关系，可以解释关联链条，直接机制或因果结论需要额外证据。

在工作目录执行 `python /skills/weekly-skill/scripts/prepare.py 案例ID 索引目录 原始文件 [其他文件 ...]`。支持 UTF-8 文本、Markdown、逐行配置与 DOCX 正文段落和表格；原生文字 PDF 可选用 pypdf（Python 包），没有时用评测环境已有 PDF 阅读器转录。生成的 source.txt 和 inventory.json 保留原文块、来源位置、文件指纹和引文行号。把本题中间 JSON 与 source.txt 放在同一目录，按需选用 evidence 或 source_blocks。PDF 多栏、扫描页、Word 合并单元格、页眉脚注和公式须对照原件；索引只帮助定位。

## 在评测环境中使用

读取 /input/case.json、task.md、output_contract 和实际附件。记录 case_id、任务语言、受众、指定格式与证据范围。把下面示例中的字段换成当前案例的实际材料。先在 /app/work 处理，最终把成稿、必要的可编辑附件和 /app/output/result.json 放入 /app/output。保留原 output_contract 的字段名、类型与 case_id，将主结果、来源、修改记录、未解问题和状态填入相应字段。review.json 是本地机械检查的报告；语义判断、任务覆盖及正式结果须由执行 Agent 完成。材料缺失时交付可核查部分，标明缺失处。若案例要求 Office 或图形产物，生成指定格式，并打开实际渲染的 PDF/PNG 预览检查。

## 最小调用示例

最终成稿可先写成 /app/work/draft.json，将所需独立产物写到 /app/output，再运行 `python scripts/finish.py /input/case.json /app/work/draft.json /app/output`。用 `--artifact 文件名` 逐个检查附带的真实成品。它检验 case_id 和顶层必需字段并原子写入 result.json；若字段来自文字合同，用 `--require 字段名` 指明。字段类型、嵌套结构与科学内容仍要按案例核对。

从本 Skill 根目录运行下列命令，或将 scripts/run.py 替换为安装目录 /skills/weekly-skill 下对应的绝对路径。辅助脚本使用 Python 3.9 或更高版本及标准库。输入、引文与样例数据均为自建示例。

```sh
python scripts/run.py examples/input.json sample-output
```

示例的第三个查询返回 a → s → d 的两条证据边，端点和原句均可回查。有复核项时阅读 review.json，修正实际发现的问题后选新的输出目录重跑；脚本遇到输入格式错误会退出并说明位置。

缺端点、条件、证据或 ID 冲突的边逐条列入 graph.json 的 rejected_edges；重复 ID 的所有候选均隔离。可核验的边继续服务查询。两跳合并要求两条边有相同且明确的条件；condition_mismatches 提供不宜合并的边 ID 和各自条件，单跳观察仍可查询。不同论文的条件只有核实一致后才统一命名。

## 可复用教学示例与核验

示例的三个问题分别是方法使用什么仪器、哪些仪器测量该量、方法经哪台仪器连接到该量。answers.json 给出查询路径和逐边证据。跨论文更新时先按既有实体编号进行对齐，别名相同而来源无法确认的实体留作候选；保留旧编号并记录合并原因。

对两次输出执行 `python scripts/compare_versions.py old/graph.json new/graph.json changes.json`，可查看按 ID 归类的新增、移除和修改。对名称或方向变化的同一 ID 复核新旧证据，输出文件使用新路径。

[查看教学示例的实际输出节选](examples/output-example.md)。
