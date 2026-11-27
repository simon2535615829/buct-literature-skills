"""Infer two persistent page gutters from aligned prose rows."""
from statistics import median


def narrow_gutter(rows, width):
    # A journal gutter can be narrower than 3% of the page. Look for a
    # recurrent gap in body lines measured against their own type size.
    body = [row for row in rows if len(row) >= 6]
    if len(body) < 6:
        return None
    height = median(w["bottom"] - w["top"] for row in body for w in row)
    if height <= 0:
        return None
    best = None
    for x in range(int(width * .32), int(width * .68)+1):
        support = []
        crossed = 0
        for row in body:
            if row[0]["x0"] >= x or row[-1]["x1"] <= x:
                continue
            if any(w["x0"] <= x < w["x1"] for w in row):
                crossed += 1
                continue
            left = max(w["x1"] for w in row if w["x1"] <= x)
            right = min(w["x0"] for w in row if w["x0"] > x)
            if min(x-left, right-x) >= .35*height and right-left >= height:
                support.append(min(x-left, right-x))
        if len(support) >= max(4, .4*len(body), 2*crossed):
            rank = (len(support)-crossed, median(support), -abs(x-width/2))
            if best is None or rank > best[0]:
                best = rank, x
    return best[1] if best else None


def find_three(rows, width):
    # Require the same rows to show two distinct wide gaps separated by real text.
    grid = {}
    for i, row in enumerate(rows):
        gaps = [(a["x1"], b["x0"]) for a, b in zip(row, row[1:])
                if b["x0"] - a["x1"] >= width * .045]
        if len(gaps) < 2:
            continue
        for pct in range(15, 86, 2):
            x = pct * width / 100
            for gap in gaps:
                clearance = min(x - gap[0], gap[1] - x)
                if clearance >= .016 * width:
                    grid.setdefault(pct, {})[i] = (gap, clearance)
                    break
    best = None
    for left, a in grid.items():
        for right, b in grid.items():
            if right - left < 18:
                continue
            same = [i for i in a.keys() & b.keys() if a[i][0] != b[i][0]]
            if len(same) < 3:
                continue
            cuts = [left * width / 100, right * width / 100]
            crossed = sum(any(word["x0"] <= cut <= word["x1"] for cut in cuts for word in row) for row in rows)
            if crossed > len(same) / 2:
                continue
            score = (len(same), median(min(a[i][1], b[i][1]) for i in same),
                     median(a[i][1] + b[i][1] for i in same))
            if best is None or score > best[0]:
                best = score, cuts
    return best[1] if best else []


def split_row(row, cuts, width):
    groups = [[] for _ in range(len(cuts) + 1)]
    for word in row:
        if any(word["x0"] <= cut < word["x1"] for cut in cuts):
            return None
        lane = sum(word["x0"] > cut for cut in cuts)
        groups[lane].append(word)
    for left, right in zip(groups, groups[1:]):
        if left and right:
            minimum = width * .032
            if len(cuts) == 1:
                height = median(w["bottom"]-w["top"] for w in row)
                minimum = min(minimum, height)
            if right[0]["x0"] - left[-1]["x1"] < minimum:
                return None
    return groups
