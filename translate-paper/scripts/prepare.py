"""Create a line-addressable source transcript and a working inventory."""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def paragraph_text(p):
    parts=[]
    for node in p.iter():
        if node.tag==W+"t":
            parts.append(node.text or "")
        elif node.tag==W+"tab":
            parts.append("\t")
        elif node.tag in (W+"br",W+"cr"):
            parts.append("\n")
    return "".join(parts)

def blocks(path):
    suffix=path.suffix.lower()
    if suffix==".docx":
        with zipfile.ZipFile(path) as z:
            xml=ET.fromstring(z.read("word/document.xml"))
        body=xml.find(W+"body")
        for i,block in enumerate(body,1):
            if block.tag==W+"p":
                yield f"body block {i}",paragraph_text(block)
            elif block.tag==W+"tbl":
                for r,row in enumerate(block.findall(W+"tr"),1):
                    for c,cell in enumerate(row.findall(W+"tc"),1):
                        yield f"table block {i}, row {r}, XML cell {c}", "\n".join(
                            paragraph_text(p) for p in cell.findall(W+"p"))
    elif suffix==".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ValueError("PDF text extraction needs pypdf, or supply a verified text transcription")
        doc=PdfReader(path)
        for i,page in enumerate(doc.pages,1):
            yield f"PDF page {i}",page.extract_text() or ""
    else:
        text=path.read_text(encoding="utf-8-sig")
        lines=text.splitlines()
        if suffix not in (".md",".txt",".text"):
            for i,line in enumerate(lines,1):
                yield f"line {i}",line
        else:
            first=None
            for i,line in enumerate(lines+[""],1):
                if line.strip() and first is None:
                    first=i
                if not line.strip() and first is not None:
                    yield f"lines {first}-{i-1}","\n".join(lines[first-1:i-1])
                    first=None

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case_id")
    ap.add_argument("out",type=Path)
    ap.add_argument("files",nargs="+",type=Path)
    a=ap.parse_args()
    evidence, inventory, transcript, warnings = [],[],[],[]
    try:
        if a.out.exists() and any(a.out.iterdir()):
            raise ValueError("Choose a fresh preparation folder")
        for index,path in enumerate(a.files,1):
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            for j,(locator,fragment) in enumerate(blocks(path),1):
                if not fragment.strip():
                    if path.suffix.lower()==".pdf":
                        warnings.append(f"{path.name} {locator}: no text layer; render/OCR and verify")
                    continue
                key=f"D{index}-{digest[:8]}-B{j}"
                text=fragment.replace("\r\n","\n").replace("\r","\n").strip("\n")
                begin=len(transcript)+1
                transcript.extend(text.split("\n"))
                loc=f"{path.name} · {locator}"
                evidence.append({"id":key,"file":"source.txt","lines":[begin,len(transcript)],
                                 "quote":text,"locator":loc,"document":f"D{index}"})
                inventory.append({"id":key,"locator":loc,"text":text,"source_sha256":digest})
        a.out.mkdir(parents=True,exist_ok=True)
        (a.out/"source.txt").write_text("\n".join(transcript)+"\n",encoding="utf-8")
        value={"case_id":a.case_id,"evidence":evidence,"source_blocks":inventory,"warnings":warnings}
        (a.out/"inventory.json").write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    except (OSError,ValueError,KeyError,zipfile.BadZipFile,ET.ParseError) as exc:
        ap.exit(2,f"Cannot prepare sources: {exc}\n")

if __name__=="__main__":
    main()
