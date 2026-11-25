"""Assemble a source-linked manuscript and keep unresolved assertions in review."""
import re
from common import run

SECTIONS = ("background", "related", "gap", "contribution")


def sources(ctx, ids, docs):
    if not isinstance(ids, list):
        return [], ["Evidence must be a list of identifiers"]
    records, issues = [], []
    for key in ids:
        if not isinstance(key, str) or key not in ctx.evidence:
            issues.append(f"Unknown evidence identifier: {key}")
            continue
        row = ctx.evidence[key]
        if row.get("document") not in docs:
            issues.append(f"Unknown document for evidence {key}")
        elif row not in records:
            records.append(row)
    return records, issues


def comparison_rows(ctx, docs):
    rows = {}
    for original in ctx.data.get("comparison", []):
        doc = original["work"]
        if doc not in docs or doc in rows:
            raise ValueError(f"Unknown or duplicate comparison work: {doc}")
        refs, issues = sources(ctx, original.get("evidence", []), docs)
        for reason in issues:
            ctx.issue(doc, reason)
        verified = bool(refs) and not issues and all(e.get("document") == doc for e in refs)
        if not verified:
            ctx.issue(doc, "Comparison row lacks an excerpt from the named work")
        rows[doc] = dict(original, verified=verified)
    return rows


def compose(ctx):
    d = ctx.data
    docs = d["documents"]
    rows = comparison_rows(ctx, docs)
    sections = {s: {} for s in SECTIONS}
    ledger, accepted_gaps, seen, used = [], set(), set(), set()
    claims = d["claims"]
    if any(c["section"] not in sections for c in claims):
        raise ValueError("Unknown manuscript section")
    prior_text = {}
    for section in SECTIONS:
        for c in (c for c in claims if c["section"] == section):
            key = c["id"]
            if key in seen or not c["text"].strip():
                raise ValueError("Duplicate claim or empty prose")
            seen.add(key)
            evidence, reasons = sources(ctx, c.get("evidence", []), docs)
            papers = list(dict.fromkeys(e["document"] for e in evidence))
            roles = {docs[k]["role"] for k in papers}
            if not evidence or c.get("support", "supported") != "supported":
                reasons.append("Confirm or narrow the assertion against the quoted evidence")
            if section in ("related", "gap") and "prior" not in roles:
                reasons.append("Prior-work evidence needed")
            literal = " ".join(c["text"].split()).casefold().rstrip(".。")
            if any(role != section for role in prior_text.get(literal, ())):
                reasons.append("Repeated cross-section sentence: give each section its own evidence-supported purpose")
            if section == "gap":
                scope = c.get("scope_documents", [k for k in papers if docs[k]["role"] == "prior"])
                if not c.get("scope") or not scope or any(k not in papers or docs[k]["role"] != "prior" for k in scope):
                    reasons.append("Gap scope needs evidence from each named prior work")
            if section == "contribution":
                if "own" not in roles:
                    reasons.append("Contribution lacks evidence from the present work")
                if c.get("gap_id") not in accepted_gaps:
                    reasons.append("Contribution needs a supported gap")
            if "comparison_works" in c:
                works = list(dict.fromkeys(c["comparison_works"]))
                valid = len(works) >= 2 and all(k in papers and rows.get(k, {}).get("verified") for k in works)
                if not valid:
                    reasons.append("Source-linked comparison rows required for each work")
                elif c.get("comparison_kind") == "ranking":
                    for dim in ("dataset", "split", "metric", "protocol"):
                        values = [rows[k].get(dim) for k in works]
                        if not all(values) or any(v != values[0] for v in values):
                            reasons.append("Ranking lacks a common " + dim)
            for reason in reasons:
                ctx.issue(key, reason)
            ledger.append(dict(claim=key, section=section, text=c["text"], scope=c.get("scope"),
                               gap=c.get("gap_id"), evidence=evidence, requested_evidence=c.get("evidence", []), reasons=reasons))
            if reasons:
                if section == "contribution" and reasons == ["Contribution needs a supported gap"]:
                    quote = c.get("standalone_quote")
                    if isinstance(quote,str) and quote.strip():
                        own = [e for e in evidence if docs[e["document"]]["role"]=="own"
                               and quote.strip() in [s.strip() for s in re.split(r"(?<=[.!?。！？])\s+",e["quote"])]]
                        if own:
                            paper = own[0]["document"]
                            sections[section].setdefault(c["paragraph"],[]).append(f'“{quote.strip()}” [{paper}]')
                            used.add(paper)
                            ledger[-1]["standalone_evidence"] = own[0]["id"]
                continue
            prior_text.setdefault(literal, set()).add(section)
            if section == "gap":
                accepted_gaps.add(key)
            used.update(papers)
            sections[section].setdefault(c["paragraph"], []).append(c["text"] + " [" + ", ".join(papers) + "]")
    lines = []
    for section, paragraphs in sections.items():
        if not paragraphs:
            ctx.issue(section, "Section has no supported prose")
            continue
        lines.append("## " + d.get("headings", {}).get(section, section))
        lines.extend(" ".join(v) for v in paragraphs.values())
    requested_scope = d.get("gap_review_documents", [])
    if not isinstance(requested_scope,list) or any(k not in docs or docs[k]["role"] != "prior" for k in requested_scope):
        raise ValueError("gap_review_documents must name prior documents in the supplied packet")
    if requested_scope:
        covered = {e["document"] for entry in ledger if entry["section"]=="gap" and not entry["reasons"]
                   for e in entry["evidence"] if docs[e["document"]]["role"]=="prior"}
        for doc in sorted(set(requested_scope)-covered):
            ctx.issue(doc,"Requested gap comparison omits this prior work; cite its scope or report missing evidence")
    lines.append("## Sources")
    for k, doc in docs.items():
        if doc.get("role") == "prior" and k not in used:
            ctx.issue(k, "Prior work has no supported manuscript citation; check relevance")
        if k in used:
            fields = ("authors", "year", "title", "venue", "version", "doi", "url")
            lines.append(f"[{k}] " + " · ".join(str(doc[f]) for f in fields if doc.get(f)))
    return {"manuscript.md": "\n\n".join(lines), "claims.json": claims,
            "comparison.json": list(rows.values()), "evidence-map.json": ledger}


if __name__ == "__main__":
    run(compose)
