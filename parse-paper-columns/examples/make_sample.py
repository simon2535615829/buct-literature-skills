"""Generate a synthetic two-page table fragment. Usage: python make_sample.py output.pdf"""
import sys
from reportlab.pdfgen.canvas import Canvas

def main(path):
    doc = Canvas(path)
    for page, (label, value) in enumerate([("North", "3.4"), ("South", "5.2")], 1):
        doc.drawString(64, 780, "Table 1. Offset measurements" if page == 1 else "Table 1 (continued)")
        for y, row in [(740, ("Site", "Offset (mm)")), (715, (label, value))]:
            for x, cell in zip((70, 270), row):
                doc.drawString(x, y, cell)
        doc.drawString(64, 60, "Illustrative data - page " + str(page))
        doc.showPage()
    doc.save()

if __name__ == "__main__":
    main(sys.argv[1])
