"""Print a compact page index or the indexed evidence for selected PDF pages."""
import argparse
import json
from pathlib import Path


def render(page):
    print(f"Page {page['page']} | {page['status']}")
    if page.get("reason"):
        print(page["reason"])
    for note in page.get("limitations", []):
        print(note)
    if page.get("structure_issue"):
        print("Table extraction:", page["structure_issue"])
    for region in page.get("image_regions", []):
        print("Image", region.get("id"), region.get("bbox"), region.get("status"),
              region.get("reason", ""))
    for line in page.get("lines", []):
        print(f"{line['id']} [{line['lane']}] {line['text']}")
    for table in page.get("tables", []):
        print(f"{table['id']} {table['rows']} rows × {table['columns']} columns")
        for cell in table["cells"]:
            print(f"  r{cell['row']}c{cell['column']} "
                  f"span={cell['rowspan']}×{cell['colspan']} "
                  + json.dumps(cell["text"], ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path)
    parser.add_argument("pages", type=int, nargs="*", help="Original 1-based PDF page numbers")
    args = parser.parse_args()
    pages = json.loads(args.layout.read_bytes())["pages"]
    missing = set(args.pages) - {p["page"] for p in pages}
    if missing:
        parser.error(f"Pages absent from this extraction: {sorted(missing)}")
    for page in pages:
        if page["page"] in args.pages:
            render(page)
        elif not args.pages:
            print(f"p{page['page']} {page['status']} | {len(page.get('lines', []))} lines | "
                  f"{len(page.get('tables', []))} tables")
            for el in page.get("elements", []):
                print(f"  {el['line_id']} {el['kind']}: {el['text']}")


if __name__ == "__main__":
    main()
