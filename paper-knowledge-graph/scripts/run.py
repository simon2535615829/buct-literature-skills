from collections import Counter, defaultdict
from common import run

def unique(items):
    result={}
    for row in items:
        key=row["id"]
        if not key or key in result:
            raise ValueError(f"Empty or duplicate ID {key!r}")
        result[key]=row
    return result

def edge_context(edge):
    return tuple(edge[k] for k in ("source", "predicate", "target", "condition"))

def answer_evidence(ctx, paths, contexts):
    evidence_paths, conflicts = [], {}
    for path in paths:
        steps = []
        for edge in path:
            steps.append({"edge_id":edge["id"], "evidence":[ctx.evidence[k] for k in edge["evidence"]]})
            group = contexts[edge_context(edge)]
            if edge["polarity"] not in ("positive", "negative"):
                continue
            opposite = "negative" if edge["polarity"] == "positive" else "positive"
            if any(e["polarity"] == opposite for e in group):
                related = [e for e in group if e["polarity"] in ("positive","negative")]
                conflicts[edge_context(edge)] = {
                    "edge_ids":[e["id"] for e in related],
                    "observations":[{"id":e["id"],"polarity":e["polarity"],
                                     "evidence":[ctx.evidence[k] for k in e["evidence"]]} for e in related]}
        evidence_paths.append(steps)
    return {"evidence_paths":evidence_paths, "conflicts":list(conflicts.values())}

def graph(ctx):
    d=ctx.data
    nodes = unique(d["nodes"])
    edges, rejected = {}, []
    outward, inward = defaultdict(list), defaultdict(list)
    names, contexts = defaultdict(set), defaultdict(list)
    for key, n in list(nodes.items()):
        try:
            if not n.get("type") or not n.get("name"):
                raise ValueError("Node type and name required")
            ctx.refs(n["evidence"])
            placeholders = {"unknown", "unspecified", "unresolved", "未知", "未识别"}
            name = n["name"].strip().casefold()
            if name in placeholders and n["type"].strip().casefold() in placeholders:
                if not any(name in ctx.evidence[e]["quote"].casefold() for e in n["evidence"]):
                    raise ValueError("Unresolved placeholder node has no named referent in the cited text")
        except (KeyError, TypeError, ValueError) as exc:
            ctx.issue(key, str(exc))
            del nodes[key]
            continue
        for name in [n["name"], *n.get("aliases", [])]:
            names[" ".join(name.casefold().split())].add(n["id"])
    candidates = d["edges"]
    counts = Counter(row["id"] for row in candidates if isinstance(row,dict) and isinstance(row.get("id"),str))
    for index, e in enumerate(candidates,1):
        key = e.get("id") if isinstance(e,dict) else None
        try:
            if not isinstance(key,str) or not key.strip() or counts[key] != 1:
                raise ValueError("Missing or ambiguous edge identifier")
            ctx.refs(e.get("evidence"))
            if e.get("source") not in nodes or e.get("target") not in nodes:
                raise ValueError("Unknown source or target node")
            if not all(isinstance(e.get(k),str) and e[k].strip() for k in ("predicate","polarity","condition")):
                raise ValueError("Missing predicate, polarity or condition")
        except (TypeError, ValueError) as exc:
            rejected.append(dict(index=index, edge=e, reason=str(exc)))
            ctx.issue(f"edge {index} ({key})", str(exc))
            continue
        edges[key] = e
        outward[e["source"]].append(e)
        inward[e["target"]].append(e)
        contexts[edge_context(e)].append(e)
    # An agent may already have put suspect candidates aside. Preserve that audit trail
    # without making pre-rejected relations traversable or shadowing validated edges.
    for pos, item in enumerate(d.get("rejected_edges", []), len(candidates) + 1):
        row = item.get("edge", item) if isinstance(item, dict) else item
        if any(previous["edge"] == row for previous in rejected):
            continue
        reason = item.get("reason") if isinstance(item, dict) else None
        reason = str(reason or "Held for review in supplied rejected_edges")
        rejected.append(dict(index=pos, edge=row, reason=reason))
        ctx.issue(f"edge {pos}", reason)
    answers=[]
    for q in d["queries"]:
        start,mode=q["start"],q["mode"]
        if mode not in ("in","out","two_hop"):
            raise ValueError("Invalid query mode")
        if start not in nodes:
            choices = sorted(names.get(" ".join(start.casefold().split()), ()))
            if len(choices) != 1:
                status = "ambiguous entity" if choices else "entity not found"
                answers.append(dict(query=q, paths=[], candidates=choices, status=status,
                                    evidence_paths=[], conflicts=[]))
                continue
            start = choices[0]
        if mode=="two_hop" and not q.get("second_predicate"):
            raise ValueError("Two-hop query needs second_predicate")
        paths=[]
        mismatches=[]
        for e in (inward if mode=="in" else outward)[start]:
            if any(k in q and q[k]!=e[k] for k in ("predicate","condition","polarity")):
                continue
            if mode=="two_hop":
                for second in outward[e["target"]]:
                    matches = all(q["second_"+field] == second[field]
                                  for field in ("predicate","condition","polarity")
                                  if "second_"+field in q)
                    if matches and e["id"] != second["id"]:
                        left, right = (" ".join(edge["condition"].split()) for edge in (e,second))
                        if left == right and left.casefold() not in {"unknown","unspecified","not reported","未知","未报告"}:
                            paths.append([e,second])
                        else:
                            mismatches.append({"edges":[e["id"],second["id"]],"conditions":[left,right]})
            else:
                paths.append([e])
        answers.append({"query":q,"start_id":start,"paths":paths,"status":"matched" if paths else "no match in supplied graph",
                        "condition_mismatches":mismatches, **answer_evidence(ctx, paths, contexts)})
    return {"graph.json":{"nodes":list(nodes.values()),"edges":list(edges.values()),"rejected_edges":rejected,
            "alignment_notes":d.get("alignment_notes",[]),"evidence":list(ctx.evidence.values())},"answers.json":answers}

if __name__ == "__main__":
    run(graph)
