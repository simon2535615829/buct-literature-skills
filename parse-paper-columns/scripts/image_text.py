"""Read raster regions locally, preserving PDF coordinates and native text."""
import csv
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory


@lru_cache(maxsize=1)
def rapid_engine():
    from rapidocr_onnxruntime import RapidOCR
    return RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)


def rapid_tokens(image):
    import numpy as np
    ocr = rapid_engine()
    rgb = image.convert("RGB")
    detections, _ = ocr(np.asarray(rgb))
    pending = None
    for corners, text, confidence in detections or []:
        xs, ys = zip(*corners)
        box = (min(xs), min(ys), max(xs), max(ys))
        current = (text, box, float(confidence))
        if pending is not None:
            _, (x, y, right, bottom), _ = pending
            l, t, r, b = box
            # Two partially overlapping crops can both read the same digit.
            if x < l < right < r and min(bottom, b) - max(y, t) > max(bottom-y, b-t) / 2:
                merged = (x, min(y, t), r, max(bottom, b))
                patch = rgb.crop((max(0, math.floor(x)-2), max(0, math.floor(merged[1])-2),
                                  min(rgb.width, math.ceil(r)+2), min(rgb.height, math.ceil(merged[3])+2)))
                reading, _ = ocr(np.asarray(patch), use_det=False, use_cls=False)
                if reading and reading[0][0].strip():
                    pending = (reading[0][0], merged, float(reading[0][1]))
                    continue
            yield pending
        pending = current
    if pending is not None:
        yield pending


def recognize(image, engine, lang):
    if engine == "rapidocr":
        yield from rapid_tokens(image)

    else:
        with TemporaryDirectory() as temp:
            path = Path(temp) / "region.png"
            image.save(path)
            proc = subprocess.run(["tesseract",str(path),"stdout","-l",lang,"--psm","6","tsv"],
                                  capture_output=True,encoding="utf8",timeout=45)
            if proc.returncode:
                raise RuntimeError(proc.stderr.strip()[-300:])
            for row in csv.DictReader(io.StringIO(proc.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
                if row["level"] == "5" and row["text"].strip():
                    x,y,w,h = (int(row[k]) for k in ("left","top","width","height"))
                    yield row["text"], (x,y,x+w,y+h), float(row["conf"])/100


def read_images(page, native, engine, lang):
    regions, jobs, words = [], [], []
    seen = set()
    for obj in page.images:
        box = (max(page.bbox[0], obj["x0"]), max(page.bbox[1], obj["top"]),
               min(page.bbox[2], obj["x1"]), min(page.bbox[3], obj["bottom"]))
        if box in seen or box[2] <= box[0] or box[3] <= box[1]:
            continue
        seen.add(box)
        region = dict(id=f"p{page.page_number}-im{len(regions)+1}", bbox=box,
                      status="needs_visual_read", reason="OCR disabled")
        index = len(regions)
        regions.append(region)
        if engine == "off":
            continue
        size = obj.get("srcsize") or (0, 0)
        thin_at_source_and_on_page = any(
            0 < pixels < 8 and points < 2
            for pixels, points in zip(size, (box[2]-box[0], box[3]-box[1]))
        )
        if min(size) == 1 or (native and thin_at_source_and_on_page):
            region["reason"] = "Raster fragment too thin for independent text recognition"
            continue
        region["reason"] = "OCR worker did not finish this region"
        jobs.append(dict(index=index, box=box, size=size))
    if not jobs:
        return regions, words

    backend = engine if engine != "auto" else ("tesseract" if shutil.which("tesseract") else "rapidocr")
    request = dict(path=os.fspath(page.pdf.stream.name), page=page.page_number,
                   box=page.bbox, rotation=page.rotation, jobs=jobs, native=native,
                   backend=backend, lang=lang)
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", OMP_THREAD_LIMIT="1")
    try:
        proc = subprocess.run([sys.executable, __file__], input=json.dumps(request).encode(),
                              capture_output=True, env=env, timeout=100)
        output = proc.stdout
        failure = f"OCR worker exit {proc.returncode}" if proc.returncode else None
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or b""
        failure = "OCR worker timeout"
    except OSError as exc:
        output, failure = b"", f"OCR worker unavailable: {exc}"
    pending = {j["index"] for j in jobs}
    for line in output.splitlines():
        try:
            index, update, added = json.loads(line)
            if index not in pending:
                continue
            pending.remove(index)
            regions[index].pop("reason")
            regions[index].update(update)
            accepted = []
            for w in added:
                overlap = [v for v in words if w["x0"]-1 <= (v["x0"]+v["x1"])/2 <= w["x1"]+1
                           and w["top"]-1 <= (v["top"]+v["bottom"])/2 <= w["bottom"]+1]
                joined = "".join(v["text"] for v in sorted(overlap, key=lambda v:v["x0"]))
                if re.sub(r"\s+", "", joined).casefold() != re.sub(r"\s+", "", w["text"]).casefold():
                    accepted.append(dict(w, region=regions[index]["id"]))
            if added:
                regions[index]["added"] = len(accepted)
                if not accepted:
                    regions[index]["status"] = "covered_by_prior_ocr"
            words.extend(accepted)
        except (ValueError, KeyError, TypeError):
            continue
    if failure:
        for index in pending:
            regions[index]["reason"] = failure
    return regions, words


def region_image(pdfpage, request, job):
    x, y, r, b = job["box"]
    ox, oy, right, bottom = request["box"]
    width, height = r-x, b-y
    iw, ih = job["size"]
    scale = min(max(250/72, min(iw/width, ih/height)), 4096/max(width,height),
                math.sqrt(5_000_000/(width*height)))
    # PDFium applies crop margins in the displayed orientation, after rotation.
    pw, ph = pdfpage.get_size()
    if abs(pw-(right-ox)) > 1 or abs(ph-(bottom-oy)) > 1:
        raise ValueError("Render box and extraction box differ")
    margins = (x-ox, bottom-b, right-r, y-oy)
    bitmap = pdfpage.render(scale=scale, crop=tuple(max(0, v) for v in margins))
    try:
        return bitmap.to_pil().convert("RGB")
    finally:
        bitmap.close()


def inspect_region(pdfpage, request, job):
    from PIL import ImageDraw
    image = region_image(pdfpage, request, job)
    x, y, r, b = job["box"]
    sx, sy = image.width/(r-x), image.height/(b-y)
    draw = ImageDraw.Draw(image)
    covered = False
    for word in request["native"]:
        if not word["text"].strip() or "\ufffd" in word["text"] or "(cid:" in word["text"]:
            continue
        left, top = max(x, word["x0"]), max(y, word["top"])
        right, bottom = min(r, word["x1"]), min(b, word["bottom"])
        if right > left and bottom > top:
            draw.rectangle(((left-x)*sx, (top-y)*sy, (right-x)*sx, (bottom-y)*sy), fill="white")
            covered = True
    ink = image.convert("L").point(lambda value: 255 if value < 235 else 0).getbbox()
    if not ink:
        return dict(status="native_text_confirmed" if covered else "no_visible_ink", added=0), []
    if request["backend"] == "rapidocr":
        # The neural detector uses the surrounding margins to segment text.
        ink = (0, 0, image.width, image.height)
    left, top = max(0, ink[0]-8), max(0, ink[1]-8)
    crop = image.crop((left, top, min(image.width, ink[2]+8), min(image.height, ink[3]+8)))
    backend = request["backend"]
    words = []
    for value, (a,c,d,e), conf in recognize(crop, backend, request["lang"]):
        words.append(dict(text=value, x0=x+(left+a)/sx, top=y+(top+c)/sy,
                          x1=x+(left+d)/sx, bottom=y+(top+e)/sy, confidence=round(conf,3)))
    if not words:
        return dict(status="needs_visual_read", engine=backend, reason="No text recognized in residual image"), []
    return dict(status="verify_ocr", engine=backend, added=len(words),
                low_confidence=any(w["confidence"] < .75 for w in words)), words


def worker():
    request = json.load(sys.stdin)
    if sys.platform.startswith("linux"):
        import resource
        # Leave room for the native parser, renderer and external OCR process.
        cap = (1408 if request["backend"] == "rapidocr" else 640) * 1024**2
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        limits = [n for n in (cap, soft, hard) if n != resource.RLIM_INFINITY]
        resource.setrlimit(resource.RLIMIT_AS, (min(limits), hard))
    import pypdfium2 as pdfium
    with pdfium.PdfDocument(request["path"]) as doc:
        page = doc[request["page"]-1]
        try:
            for job in request["jobs"]:
                try:
                    update, words = inspect_region(page, request, job)
                except Exception as exc:
                    update, words = dict(status="needs_visual_read", reason=str(exc)[-350:]), []
                print(json.dumps([job["index"], update, words]), flush=True)
        finally:
            page.close()


if __name__ == "__main__":
    worker()


