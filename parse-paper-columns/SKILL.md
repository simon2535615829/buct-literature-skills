---
name: parse-paper-columns
description: Parse native-text scientific PDFs into page-anchored lines, repair reading order across two-column sections and spanning headings, and use rendered evidence to answer document-parsing tasks.
---

# Parse a paper with recoverable evidence

Start by extracting all pages, including image regions on pages with selectable text. Read each page's image_regions alongside lines and tables. For a mixed page, verify the image-derived reading, unit and inequality against its bounding box even when the native title is correct. Each recognized item in a line's ocr list contains its region, page coordinates and confidence. A needs_visual_read region requires visual inspection even when other regions succeeded. Keep uncertain symbols explicit in the final result.

Auto mode tries a local Tesseract executable and then an installed RapidOCR engine. For Chinese with Tesseract use `--ocr-lang chi_sim+eng` when those language packs are installed. On Python 3.9–3.12, an optional CPU engine with bundled recognition models can be installed using `python -m pip install rapidocr-onnxruntime==1.4.4` where installation is available; choose it with `--ocr rapidocr`. For environments with neither engine, image region coordinates and the reason remain available for the Agent's visual reader. A figure or plot may contain labels; OCR alone does not determine their meaning.

Look up a table value by table ID, physical row, header and column, including any blank intermediate cell. The aligned_text method recovers simple unruled tables using a header, consistent column spacing and at least two numeric data rows. It accepts two-column tables near a table caption or three or more columns without one. Read method-inferred cells against the original before using the value. Wrapped labels, ambiguous alignments and continued tables need visual confirmation. For ruled grids use the physical cells and spans.

Read the case instructions, the actual PDF and the requested output fields. In the contest harness inspect /input/case.json, task.md and the supplied material paths. Use /app/work for extraction. Preserve the original case_id and every original output_contract field in /app/output/result.json. Save a partial result there early when evidence is incomplete. Complete the specific case task using the extracted evidence.

## Extract text and image regions

Run Python 3.9+ with pdfplumber 0.11.9. If missing and installation is available, run `python -m pip install pdfplumber==0.11.9`. From the installed skill directory:

```sh
python scripts/extract.py /input/paper.pdf /app/work/lines.json
```

Replace the PDF path with the actual case file. Each page contains the page size, proposed divider and ordered lines. Each line includes an ID, text, lane and bounding box in PDF points measured from the top left. Word boxes preserve the original tokens for verifying joins and reconstructing cells. Spaces in line text are inferred. For Chinese, ligatures, hyphens and mathematical symbols, compare the visible source before normalizing. Keep the raw text alongside material corrections.

**Illustrative invocation.** For a user-supplied sample.pdf with the heading “Methods”, run `python scripts/extract.py sample.pdf lines.json`. An illustrative line excerpt is `{"id":"p1-l1","text":"Methods","lane":"single","bbox":[72,50,112,62]}`. Coordinates depend on the input.

## Check the reading order and answer

For each requested field, start at its page's elements and tables. Each candidate heading, caption or numbered display points to a specific line. A ruled table has a stable page/table ID and one record per physical cell, including empty cells. For a value in column c, read every header row whose cell covers c and keep each header's unit. Verify the table title visually before associating a caption; nearby prose may refer to another table. Keep a censored entry such as "<0.05" verbatim. Borderless tables, formula typography and scans require checking the page rendering. Include the verified page, line or cell position in the case output.

1. Inspect pages containing requested evidence. The extractor searches for a persistent empty vertical strip with support on both sides. It emits the left column before the right within each band delimited by a line spanning the gutter. Compare the last line of each lane and the first line of the next with a page rendering. Staggered baselines, multiple independent gutters, centered short headings and tables can defeat this heuristic. Use the stored word boxes to reconstruct the affected region; record the page, changed order and reason.
2. Preserve the hierarchy visible in the original. Separate running headers and footers only after matching their position and content across pages. Retain footnotes, captions and bibliography as labeled elements. Join paragraphs across pages only when the sentence and typography support the join. Cite both page regions.
3. For a table, identify its caption, column boundaries and header depth from the page. Map each requested value to its row, full header path, unit and original cell location. Keep merged or empty cells explicit. Check continuation tables for repeated labels and units. For equations, inspect the rendered region for subscripts, superscripts, accents and Greek letters. Mark unresolved symbols locally.
4. Cite each extracted field with the filename, one-based PDF page and line ID or bounding box. Keep printed page labels separate. Distinguish absence in a checked region, conflicting statements and an unreadable region. For a requested answer give the finding, supporting excerpt or cell and uncertainty in the case's specified format.
5. Before saving, reopen the JSON, compare its keys with the case contract and trace each critical value back to the original PDF. Keep supporting artifacts linked from the result where the contract permits. Record which pages were read visually, OCR'd or reordered and why.

For staggered columns, the extractor checks for two vertical runs separated by whitespace and supported at neighboring heights. A gutter on an irregular page is a reading-order hypothesis. Check one sentence at each lane boundary and preserve the word boxes when correcting it.

## Handle unreadable pages

A page with no extracted words is marked needs_visual_read. Render it with an available local PDF renderer, inspect it visually or run an installed OCR engine with the appropriate language, and check any numbers and symbols against the image. A page_error contains its own failure reason. For an unavailable dependency use a local PDF viewer or another installed coordinate-aware extractor, citing page regions directly. For an inaccessible encrypted file, missing input or unavailable visual evidence, retain the case ID and requested fields, state the exact barrier and mark the affected result partial or unavailable. Never infer an experimental value from a paper title.

## 三栏正文

逐页查看 dividers_x 和每行的 lane。两道稳定的栏间空白把同一段正文分为左、中、右栏。跨栏标题和独立表格先结束前一段分栏，再继续逐栏阅读。错层排版或只有少数对齐行时，应在原页按坐标核对。

## 长文档的分段执行

先按目录定位重点页。长文档可用 --first-page 1 --last-page 8 处理首段，再用不同结果文件处理后续页段。范围包含两端，输出保留 PDF 原始页码，按页码拼接各段 pages。页面解析完成即写入临时文件，整段完成后替换目标文件。扫描页仍需保留原图坐标和未识别提示。

## 可复用教学示例与核验

跨页表先记录本页表头与单位，再比对下一页列位置；同列位置本身不足以证明表格连续。示例用两页重复表头演示保留原页坐标。执行 python examples/make_sample.py /tmp/example.pdf，然后执行 python scripts/extract.py /tmp/example.pdf /tmp/lines.json。生成示例 PDF 需要 ReportLab。

[查看教学示例的实际输出节选](examples/output-example.md)。
