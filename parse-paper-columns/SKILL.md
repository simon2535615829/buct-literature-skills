---
name: parse-paper-columns
description: Parse native-text scientific PDFs into page-anchored lines, repair reading order across two-column sections and spanning headings, and use rendered evidence to answer document-parsing tasks.
---

# 可回查的文献版面解析

先读任务和文件清单，按案例约定交出正文、结构化结果和附件。已有提取结果时直接使用；确认关键值与位置后即可成稿。需要重新提取时运行：

```sh
python scripts/extract.py paper.pdf /app/work/original-layout.json
```

结果按原页编号保存文字、栏序、图像区域、表格单元格及坐标。页上有可选文本时仍须读图像区域。小扫描框按原始像素密度局部渲染，OCR 字词带来源框；原文、乱码或不确定符号分开标注。需要特定语言时按已安装语言包选择 `--ocr-lang`。对确实无法辨认的区域报告页码、位置和缺失内容。

提取表值时把列标题、行名（可能换行）、数值或空单元格一起核对。无框表依靠同列的反复对齐；列归属含混时查看原页对应位置。保留标题、脚注、图表题注和正文的阅读次序。读取长文档可用 `--first-page` 与 `--last-page` 分段。

### 交付原始坐标与附件清单

把提取器输出留作原件。阅读时可以从中摘取几行或几列；交付的坐标附件须逐字节保留整份原件，包括所有页面、文字框和表格单元格。重建的行列及解释写进正文。已有原件时直接复用。

先把正文写入案例指定的输出路径。若合同用 `artifacts` 列出附件相对路径，可运行下面的收尾命令，将完整坐标文件原样复制到输出目录并生成 `result.json`。三个位置参数依次是案例清单、坐标原件、坐标附件名，后面列其余已写好的附件名。正文名和坐标附件名均按案例替换。

```sh
python scripts/deliver.py /input/case.json /app/work/original-layout.json layout.json final.md
```

清单从当前案例取 `case_id`，在 `artifacts` 列出实际附件。合同还有其他字段时，用 `--draft /app/work/result-draft.json` 传入已填写的内容。若合同指定其他附件结构，按原结构写清单，并用文件复制保留原始坐标。
