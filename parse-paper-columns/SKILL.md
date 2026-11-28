---
name: parse-paper-columns
description: Parse native-text scientific PDFs into page-anchored lines, repair reading order across two-column sections and spanning headings, and use rendered evidence to answer document-parsing tasks.
---

# 可回查的文献版面解析

先读 /input/case.json 和 task.md，找到案例提供的实际 PDF。官方将本 Skill 安装在 /skills/weekly-skill。下面的命令可从 /app/work 运行，把输入文件名换成实际路径。

```sh
python /skills/weekly-skill/scripts/extract.py /input/paper.pdf /app/work/original-layout.json
```

提取器优先保留原生文字和词框，仅在嵌图中识别原生词框以外的可见内容。默认使用已安装的 Tesseract，缺少它时尝试 RapidOCR。扫描词带来源框和置信度，可用 `--ocr-lang` 指定已安装的 Tesseract 语言包。局部识别失败时，原生文字与已完成区域仍保留。对答案相关的 `needs_visual_read` 区域核对原页，读不清时注明页码、位置和缺口。缺少 pdfplumber 时会尝试 pdftotext，保留原生文字和词框。

提取表值时把列标题、行名（可能换行）、数值或空单元格一起核对。无框表依靠同列的反复对齐；列归属含混时查看原页对应位置。保留标题、脚注、图表题注和正文的阅读次序。读取长文档可用 `--first-page` 与 `--last-page` 分段。

先查看页索引，再按题目读取目标页。下例中的 2 是原 PDF 的物理页码。页视图列出带行号的正文、图像状态，以及带行列号、跨度和空值的表格单元格。

```sh
python /skills/weekly-skill/scripts/read_page.py /app/work/original-layout.json
python /skills/weekly-skill/scripts/read_page.py /app/work/original-layout.json 2
```

同页含双栏正文和通栏图注时，提取器先检测整页栏线；整页不成立时再从有垂直间隔或表格边界的局部文字带中寻找反复出现的栏隙。局部栏线记在该页的 `column_regions` 中。引用时保留页码和行号（例如 `p2-l3`）；需要精确位置时回查同一行的 `bbox` 或原始词框。栏隙证据不足、图中文字异常或跨页接续不清时，结合原页核对。

### 交付原始坐标与附件清单

按案例的 output_contract 交付。案例要求原始坐标附件时，保留整份提取器输出；重建的行列及解释写进正文。若案例只要答案和来源，可直接引用原页和区块。

先把正文写入案例指定的输出路径。若合同用 `artifacts` 列出附件相对路径，可运行下面的收尾命令，将完整坐标文件原样复制到输出目录并生成 `result.json`。三个位置参数依次是案例清单、坐标原件、坐标附件名，后面列其余已写好的附件名。正文名和坐标附件名均按案例替换。

```sh
python /skills/weekly-skill/scripts/deliver.py /input/case.json /app/work/original-layout.json layout.json final.md
```

清单从当前案例取 `case_id`，在 `artifacts` 列出实际附件。合同还有其他字段时，用 `--draft /app/work/result-draft.json` 传入已填写的内容。若合同指定其他附件结构，按原结构写清单，并用文件复制保留原始坐标。
