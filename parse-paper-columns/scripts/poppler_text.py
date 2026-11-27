"""Read native PDF lines and word boxes with Poppler when pdfplumber is unavailable."""
import shutil
import subprocess
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory


def bounds(node):
    return [float(node.attrib[k]) for k in ("xMin", "yMin", "xMax", "yMax")]


def page_nodes(path):
    parser = ET.XMLPullParser(events=("end",))
    with path.open(encoding="utf-8", errors="replace") as source:
        for line in source:
            # PDF font mappings sometimes emit XML-forbidden glyphs inside words.
            # Retain a visible unknown at that position instead of losing the page.
            parser.feed(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]", "\ufffd", line))
            for _, node in parser.read_events():
                if node.tag.rsplit("}", 1)[-1] == "page":
                    yield node
                    node.clear()
    parser.close()


def pages(pdf, first, last):
    if not shutil.which("pdftotext"):
        raise RuntimeError("Neither pdfplumber nor pdftotext is available. Use the runtime's declared PDF reader or renderer.")
    with TemporaryDirectory() as tmp:
        xml = Path(tmp) / "layout.xhtml"
        command = ["pdftotext", "-bbox-layout", "-enc", "UTF-8", "-f", str(first)]
        if last is not None:
            command += ["-l", str(last)]
        subprocess.run(command + [str(pdf.resolve()), str(xml)], check=True)
        count = 0
        for page in page_nodes(xml):
            number = first + count
            count += 1
            lines = []
            for line in page.findall(".//{*}line"):
                words = [[w.text, *bounds(w)] for w in line.findall("{*}word") if w.text]
                if words:
                    lines.append(dict(id=f"p{number}-l{len(lines)+1}", lane="native",
                                      bbox=bounds(line), words=words,
                                      text=" ".join(w[0] for w in words)))
            yield dict(page=number, size=[float(page.attrib[k]) for k in ("width","height")],
                       backend="pdftotext", lines=lines, tables=[], image_regions=[],
                       status="partial_native_text" if lines else "needs_visual_read",
                       limitations=["Only native text and word boxes were extracted. Inspect the rendered page for images, table cells and uncertain symbols."])
        if not count or (last is not None and count != last-first+1):
            raise ValueError("Requested page range exceeds the document")
