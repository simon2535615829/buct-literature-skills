"""Read raster regions locally, preserving PDF coordinates and native text."""
import csv
import io
import math
import re
import shutil
import subprocess
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
    regions, added, seen = [], [], set()
    rendered = None
    errors = {}
    for obj in page.images:
        box = (max(page.bbox[0],obj["x0"]), max(page.bbox[1],obj["top"]),
               min(page.bbox[2],obj["x1"]), min(page.bbox[3],obj["bottom"]))
        if box in seen or box[2] <= box[0] or box[3] <= box[1]:
            continue
        seen.add(box)
        region = dict(id=f"p{page.page_number}-im{len(regions)+1}",bbox=box,status="needs_visual_read")
        regions.append(region)
        if engine == "off":
            region["reason"] = "OCR disabled"
            continue
        try:
            if rendered is None:
                dpi = min(250, 72*math.sqrt(12_000_000/(page.width*page.height)))
                rendered = page.to_image(resolution=dpi,force_mediabox=True).original
            sx,sy = rendered.width/page.width, rendered.height/page.height
            ox,oy = page.bbox[:2]
            px=(math.floor((box[0]-ox)*sx), math.floor((box[1]-oy)*sy),
                math.ceil((box[2]-ox)*sx), math.ceil((box[3]-oy)*sy))
            crop = rendered.crop(px)
            # A small inset can contain many more source pixels than the page preview.
            # Render only its rectangle at source density; keep the same PDF coordinates.
            width, height = box[2]-box[0], box[3]-box[1]
            iw, ih = obj.get("srcsize") or (0, 0)
            scale = min(iw/width, ih/height, math.sqrt(8_000_000/(width*height)))
            origin_x, origin_y = ox + px[0]/sx, oy + px[1]/sy
            if scale > 1.25*max(sx,sy) and not page.rotation:
                try:
                    import pypdfium2 as pdfium
                    with pdfium.PdfDocument(page.pdf.stream) as document:
                        pdfpage = document[page.page_number-1]
                        try:
                            pw, ph = pdfpage.get_size()
                            if abs(pw-page.width)<1 and abs(ph-page.height)<1:
                                margins = (box[0]-ox, ph-(box[3]-oy), pw-(box[2]-ox), box[1]-oy)
                                bitmap = pdfpage.render(scale=scale, crop=tuple(max(0,v) for v in margins))
                                try:
                                    crop = bitmap.to_pil().copy()
                                finally:
                                    bitmap.close()
                                sx, sy = crop.width/width, crop.height/height
                                origin_x, origin_y = box[:2]
                        finally:
                            pdfpage.close()
                except (ImportError, OSError, ValueError, RuntimeError):
                    # The existing page crop stays usable when higher-resolution rendering is unavailable.
                    pass
            engines = [engine]
            if engine=="auto":
                engines = ["tesseract"] if shutil.which("tesseract") else []
                engines.append("rapidocr")
            messages = []
            tokens = []
            for backend in engines:
                if backend in errors:
                    messages.append(errors[backend])
                    continue
                try:
                    tokens=list(recognize(crop,backend,lang))
                    if tokens:
                        region["engine"]=backend
                        break
                    messages.append(backend+": no text recognized")
                except Exception as exc:
                    message=backend+": "+str(exc)[:250]
                    if isinstance(exc,(ImportError,FileNotFoundError)):
                        errors[backend]=message
                    messages.append(message)
            if not tokens:
                region["reason"]="; ".join(messages)
                continue
            kept, low = 0, False
            for text, (x,y,r,b), conf in tokens:
                x,r=origin_x+x/sx,origin_x+r/sx
                y,b=origin_y+y/sy,origin_y+b/sy
                overlap=[w for w in native+added if x-2 <= (w["x0"]+w["x1"])/2 <= r+2 and y-2 <= (w["top"]+w["bottom"])/2 <= b+2]
                normalize=lambda s: re.sub(r"\s+","",s).casefold()
                if normalize("".join(w["text"] for w in sorted(overlap,key=lambda w:w["x0"]))) == normalize(text):
                    continue
                added.append(dict(text=text,x0=x,x1=r,top=y,bottom=b,region=region["id"],
                                  confidence=round(conf,3) if conf is not None else None))
                kept+=1
                low |= conf is not None and conf < .75
            region.update(status="verify_ocr" if kept else "native_text_confirmed", added=kept, low_confidence=low)
        except Exception as exc:
            region["reason"]=str(exc)[:300]
    return regions, added
