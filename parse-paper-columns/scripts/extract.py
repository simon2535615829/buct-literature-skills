"""Extract coordinate-bearing lines from native-text scientific PDFs."""
import argparse
from bisect import bisect_left
import json
import re
import statistics
from tempfile import NamedTemporaryFile
from pathlib import Path

import pdfplumber
from borderless import infer
from columns import find_three, split_row
from image_text import read_images


def bbox(words):
    return [round(f(w[k] for w in words), 2) for k, f in
            (("x0", min), ("top", min), ("x1", max), ("bottom", max))]


def rows_of(words):
    rows = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows:
            anchor = rows[-1][0]
            overlap = min(anchor["bottom"], word["bottom"]) - max(anchor["top"], word["top"])
            height = max(anchor["bottom"] - anchor["top"], word["bottom"] - word["top"])
            if abs(word["top"] - anchor["top"]) <= 2.5 or overlap > height / 2:
                rows[-1].append(word)
                continue
        rows.append([word])
    return [sorted(row, key=lambda w: w["x0"]) for row in rows]



def find_divider(rows, width):
    # A gutter should stay empty across rows and have text on both sides.
    # A short gap inside a sentence is too narrow to qualify.
    candidates = []
    for pct in range(32, 69):
        x = width * pct / 100
        gaps = []
        crossings = 0
        for row in rows:
            left = [w["x1"] for w in row if w["x1"] < x]
            right = [w["x0"] for w in row if w["x0"] > x]
            if any(w["x0"] <= x <= w["x1"] for w in row):
                crossings += 1
            elif left and right and min(x-max(left), min(right)-x) >= width * .016:
                gaps.append(min(x-max(left), min(right)-x))
        if len(gaps) >= 3 and len(gaps) >= 2 * crossings:
            candidates.append((len(gaps)-crossings, statistics.median(gaps), -abs(50-pct), x))
    if candidates:
        return max(candidates)[-1]

    # Staggered columns can have no shared baseline. Look for two overlapping
    # vertical runs of complete lines separated by a persistent whitespace strip.
    if len(rows) < 6:
        return None
    row_height = statistics.median(max(w["bottom"] for w in row) - min(w["top"] for w in row) for row in rows)
    staggered = []
    for pct in range(32, 69):
        divider = width * pct / 100
        margin = width * .016
        left = [row for row in rows if row[-1]["x1"] < divider - margin]
        right = [row for row in rows if row[0]["x0"] > divider + margin]
        if min(len(left), len(right)) < 3 or len(left) + len(right) < .85 * len(rows):
            continue
        def paired(group, other):
            tops = [r[0]["top"] for r in other]
            count = 0
            for row in group:
                y = row[0]["top"]
                i = bisect_left(tops, y)
                if any(abs(y - top) <= 1.5 * row_height for top in tops[max(0, i-1):i+1]):
                    count += 1
            return count
        support = min(paired(left, right), paired(right, left))
        if support < 3 or support < .6 * min(len(left), len(right)):
            continue
        clearance = min(divider - max(r[-1]["x1"] for r in left),
                        min(r[0]["x0"] for r in right) - divider)
        staggered.append((support, clearance, -abs(50-pct), divider))
    return max(staggered)[-1] if staggered else None


CAPTION = re.compile(r"^(Table|Tab\.|Figure|Fig\.|表|图)\s*(S?\d+(?:[.-]\d+)*)\b", re.I)
HEADING = re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+[^\d]|abstract$|references$|摘要$|参考文献$)", re.I)


def elements_of(lines):
    elements = []
    for line in lines:
        text = line["text"]
        caption = CAPTION.match(text)
        if caption:
            kind = "caption_candidate"
        elif HEADING.match(text) and len(text) <= 110:
            kind = "heading_candidate"
        elif re.search(r"[(（]\d+[a-z]?[)）]\s*$", text) and re.search(r"[=≈≠∑∫<>]", text):
            kind = "numbered_equation_candidate"
        else:
            continue
        elements.append({"kind": kind, "line_id": line["id"], "text": text, "bbox": line["bbox"]})
    return elements


def ruled_tables(page, words):
    tables = []
    for index, table in enumerate(page.find_tables(), 1):
        xs = sorted({v for box in table.cells for v in (box[0], box[2])})
        ys = sorted({v for box in table.cells for v in (box[1], box[3])})
        cells = []
        for x, y, right, bottom in sorted(table.cells, key=lambda b: (b[1], b[0])):
            inside = [w for w in words if x <= (w["x0"] + w["x1"])/2 < right
                      and y <= (w["top"] + w["bottom"])/2 < bottom]
            content = "\n".join(" ".join(w["text"] for w in row) for row in rows_of(inside))
            row, col = ys.index(y), xs.index(x)
            cells.append({"row": row+1, "column": col+1, "rowspan": ys.index(bottom)-row,
                          "colspan": xs.index(right)-col, "bbox": [x,y,right,bottom], "text": content})
        tables.append({"id": f"p{page.page_number}-t{index}", "bbox": list(table.bbox),
                       "rows": len(ys)-1, "columns": len(xs)-1, "cells": cells})
    return tables


def parse_page(page, engine, lang):
    native = page.extract_words(x_tolerance=2, y_tolerance=2)
    regions, recognized = read_images(page, native, engine, lang)
    words = native + recognized
    rows = rows_of(words)
    issue = None
    try:
        tables = ruled_tables(page, words)
        tables.extend(infer(page, rows, tables))
    except (ValueError, ArithmeticError, IndexError) as error:
        issue, tables = str(error), []
    def table_for(row):
        for table in tables:
            x,y,r,b=table["bbox"]
            if all(x-.1 <= (w["x0"]+w["x1"])/2 <= r+.1 and y-.1 <= (w["top"]+w["bottom"])/2 <= b+.1 for w in row):
                return table["id"]
        return None
    row_tables=[table_for(row) for row in rows]
    prose = [row for row, table in zip(rows, row_tables) if not table]
    cuts = find_three(prose, page.width)
    if not cuts:
        divider = find_divider(prose, page.width)
        cuts = [divider] if divider is not None else []
    lanes = ("left", "middle", "right") if len(cuts) == 2 else ("left", "right")
    buffers = [[] for _ in lanes]
    lines = []

    def emit(group, lane, table=None):
        for row in group:
            lines.append(dict(id=f"p{page.page_number}-l{len(lines)+1}",
                              bbox=bbox(row), lane=lane,
                              text=" ".join(w["text"] for w in row),
                              words=[[w["text"], *bbox([w])] for w in row]))
            if table:
                lines[-1]["table_id"]=table
            ocr=[{"region":w["region"],"text":w["text"],"confidence":w["confidence"],"bbox":bbox([w])}
                 for w in row if "region" in w]
            if ocr:
                lines[-1]["ocr"]=ocr

    def flush():
        for lane, group in zip(lanes, buffers):
            emit(group, lane)
            group.clear()

    for row, table in zip(rows, row_tables):
        if table:
            flush()
            emit([row], "table", table)
        elif not cuts:
            emit([row], "single")
        else:
            groups = split_row(row, cuts, page.width)
            if groups is None:
                flush()
                emit([row], "spanning")
            else:
                for group, words in zip(buffers, groups):
                    if words:
                        group.append(words)
    flush()
    result = dict(page=page.page_number, size=[float(page.width), float(page.height)],
                divider_x=cuts[0] if len(cuts) == 1 else None, dividers_x=cuts, status="review_layout" if lines else "needs_visual_read",
                lines=lines)
    result["elements"] = elements_of(lines)
    result["tables"] = tables
    result["image_regions"] = regions
    if issue:
        result["structure_issue"]=issue
    if any(r["status"]=="needs_visual_read" for r in regions):
        result["status"]="needs_visual_read"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("json", type=Path)
    parser.add_argument("--ocr",choices=("auto","tesseract","rapidocr","off"),default="auto")
    parser.add_argument("--ocr-lang",default="eng",help="Tesseract language packs, e.g. chi_sim+eng")
    parser.add_argument("--first-page", type=int, default=1, help="First page to read, counted from 1")
    parser.add_argument("--last-page", type=int, help="Last page to read, inclusive")
    args = parser.parse_args()
    if args.first_page < 1 or (args.last_page is not None and args.last_page < args.first_page):
        parser.error("Choose a positive, increasing page range")
    if args.pdf.resolve() == args.json.resolve():
        parser.error("Use a separate output path.")
    args.json.parent.mkdir(parents=True, exist_ok=True)
    part = None
    try:
        with pdfplumber.open(args.pdf) as doc:
            last = args.last_page if args.last_page is not None else len(doc.pages)
            if last > len(doc.pages) or args.first_page > len(doc.pages):
                parser.error("Requested page range exceeds the document")
            with NamedTemporaryFile(mode="w", encoding="utf8", dir=args.json.parent,
                                    delete=False, suffix=".json.tmp") as stream:
                part = Path(stream.name)
                stream.write('{"source":' + json.dumps(args.pdf.name, ensure_ascii=False) + ',"pages":[')
                for number in range(args.first_page, last + 1):
                    page = doc.pages[number - 1]
                    try:
                        result = parse_page(page, args.ocr, args.ocr_lang)
                    except Exception as exc:
                        result = dict(page=number, status="page_error", reason=str(exc))
                    finally:
                        page.close()
                    if number > args.first_page:
                        stream.write(",")
                    json.dump(result, stream, ensure_ascii=False)
                stream.write("]}")
        part.replace(args.json)
    except Exception as exc:
        parser.exit(2, f"Cannot parse {args.pdf.name}: {exc}\\n")
    finally:
        if part is not None:
            part.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
