"""Infer simple unruled tables from headers and repeated aligned data cells."""
import bisect
import re
import statistics

CAPTION = re.compile(r"^(?:Table|Tab\.|表)\s*S?\d+",re.I)
VALUE = re.compile(r"(?:[<>≤≥≈~±+−-]?\s*)?(?:\d+(?:[.,]\d+)*|\.\d+)(?:\s*(?:%|±|–|[-+/]|[Ee][+-]?\d|[a-zA-Zμµ°]).*)?$")


def bounds(words):
    return [min(w["x0"] for w in words),min(w["top"] for w in words),
            max(w["x1"] for w in words),max(w["bottom"] for w in words)]


def runs(row, gap):
    groups = []
    for w in row:
        if not groups or w["x0"] - groups[-1][-1]["x1"] >= gap:
            groups.append([])
        groups[-1].append(w)
    return groups


def intersects(a,b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def infer(page,rows,ruled):
    tables=[]
    skip=0
    for i,header in enumerate(rows):
        if i<skip or i+2>=len(rows):
            continue
        title=" ".join(w["text"] for w in rows[i-1]) if i else ""
        height=max(1,statistics.median(w["bottom"]-w["top"] for w in header))
        caption=bool(CAPTION.match(title)) and header[0]["top"]-rows[i-1][0]["top"]<6*height
        groups=runs(header,max(10,height*1.25))
        if len(groups)<(2 if caption else 3) or any(VALUE.fullmatch(" ".join(w["text"] for w in g)) for g in groups):
            continue
        edges=[(left[-1]["x1"]+right[0]["x0"])/2 for left,right in zip(groups,groups[1:])]
        matrix=[groups]
        end=i+1
        for index in range(i+1,len(rows)):
            row=rows[index]
            prev=rows[index-1]
            if row[0]["top"]-prev[0]["top"]>3.3*height:
                break
            cells=[[] for _ in groups]
            for w in row:
                idx=bisect.bisect_right(edges,(w["x0"]+w["x1"])/2)
                if any(w["x0"]+1<edge<w["x1"]-1 for edge in edges):
                    break
                cells[idx].append(w)
            else:
                texts=[" ".join(w["text"] for w in cell) for cell in cells]
                if sum(bool(s) for s in texts)>=2 and any(VALUE.fullmatch(s) for s in texts[1:]):
                    matrix.append(cells)
                    end=index+1
                    continue
                # Join a close, label-only continuation between two populated rows.
                # Require geometric support on both sides to avoid absorbing notes below the table.
                if (len(matrix)>1 and texts[0] and not any(texts[1:]) and index+1<len(rows)
                        and matrix[-1][0] and abs(row[0]["x0"]-matrix[-1][0][0]["x0"]) < height
                        and row[0]["top"]-prev[0]["top"] <= 1.6*height
                        and rows[index+1][0]["top"]-row[0]["top"] > row[0]["top"]-prev[0]["top"]
                        and rows[index+1][0]["top"]-row[0]["top"] <= 3.3*height
                        and any(w["x0"]>edges[0] and VALUE.fullmatch(w["text"]) for w in rows[index+1])):
                    matrix[-1][0].extend(cells[0])
                    end=index+1
                    continue
            break
        if len(matrix)<3:
            continue
        box=bounds([w for row in matrix for cell in row for w in cell])
        if any(intersects(box,t["bbox"]) for t in ruled):
            continue
        cells=[]
        cols=[box[0],*edges,box[2]]
        for ri,row in enumerate(matrix,1):
            y=bounds([w for cell in row for w in cell])
            for ci,cell in enumerate(row,1):
                cells.append(dict(row=ri,column=ci,rowspan=1,colspan=1,
                                  bbox=[cols[ci-1],y[1],cols[ci],y[3]],
                                  text=" ".join(w["text"] for w in cell)))
        tables.append(dict(id=f"p{page.page_number}-u{len(tables)+1}",bbox=box,method="aligned_text",
                           rows=len(matrix),columns=len(groups),cells=cells,caption=title if caption else None))
        skip=end
    return tables
