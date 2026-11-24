"""Infer two persistent page gutters from aligned prose rows."""
from statistics import median


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
        if left and right and right[0]["x0"] - left[-1]["x1"] < width * .032:
            return None
    return groups
