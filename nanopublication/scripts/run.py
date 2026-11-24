import hashlib
import json
from urllib.parse import quote
from common import run
from conditions import select_support

NP = "http://www.nanopub.org/nschema#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
PROV = "http://www.w3.org/ns/prov#"
EX = "urn:paper-skill:"
def iri(value):
    return "<" + value + ">"

def literal(value):
    return json.dumps(value, ensure_ascii=False)

def review_claim(ctx, claim, docs):
    reasons = []
    fields = ("subject", "relation", "object", "condition", "polarity", "modality", "confidence_basis")
    for field in fields:
        if not isinstance(claim.get(field), str) or not claim[field].strip():
            reasons.append("Missing assertion field " + field)
    support = claim.get("support", "direct")
    if support not in ("direct", "inferred"):
        reasons.append(claim.get("reason") or "Source support needs review: " + str(support))
    if support == "inferred" and not (isinstance(claim.get("derivation"), str) and claim["derivation"].strip()):
        reasons.append("Specify how the cited observations lead to the inference")
    ids = claim.get("evidence")
    if not isinstance(ids, list) or not ids:
        reasons.append("No evidence supplied")
    else:
        for key in ids:
            if not isinstance(key, str) or key not in ctx.evidence:
                reasons.append(f"Unknown evidence: {key}")
            elif ctx.evidence[key].get("document") not in docs:
                reasons.append(f"Unknown document for {key}")
        if "bindings" in claim and not isinstance(claim["bindings"], dict):
            reasons.append("Bindings must name the assertion fields")
        elif "bindings" in claim:
            for field in ("subject", "relation", "object", "condition"):
                binding = claim["bindings"].get(field, {})
                if not isinstance(binding, dict):
                    reasons.append(f"Malformed source fragment for {field}")
                    continue
                source = binding.get("evidence")
                fragment = binding.get("text")
                if not isinstance(source, str) or source not in ids or source not in ctx.evidence or not isinstance(fragment, str) or not fragment.strip():
                    reasons.append(f"Missing source fragment for {field}")
                elif fragment not in ctx.evidence[source]["quote"]:
                    reasons.append(f"Fragment for {field} is absent from the cited excerpt")
    spans = []
    if not reasons:
        spans, issue = select_support(claim, [ctx.evidence[k] for k in ids])
        if issue:
            reasons.append(issue)
    return reasons, spans

def publish(ctx):
    docs = ctx.data["documents"]
    quads, records, seen = [], [], set()
    pending = []
    for index, c in enumerate(ctx.data["claims"], 1):
        reasons, spans = review_claim(ctx, c, docs)
        if reasons:
            pending.append({"index":index, "claim":c, "reasons":reasons})
            ctx.issue(f"candidate {index}", " / ".join(reasons))
            continue
        evidence_ids = sorted({span["evidence"] for span in spans} if spans else set(c["evidence"]))
        refs = [ctx.evidence[k] for k in evidence_ids]
        if any(e.get("document") not in docs for e in refs):
            raise ValueError("Unknown source document")
        metadata = {e["document"]: docs[e["document"]] for e in refs}
        creator = ctx.data["creator"]
        if not isinstance(creator, str) or not creator.strip():
            raise ValueError("Publication creator missing")
        record = dict(c, evidence=evidence_ids, support=c.get("support", "direct"))
        if spans:
            record["supporting_clauses"] = spans
        identity = [record, refs, metadata, creator]
        digest = hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        base = EX + digest
        if base in seen:
            continue
        seen.add(base)
        def add(s,p,o,g):
            quads.append(f"{iri(s)} {iri(p)} {o} {iri(base+'#'+g)} .")
        add(base,RDF+"type",iri(NP+"Nanopublication"),"head")
        for link,g in (("hasAssertion","assertion"),("hasProvenance","provenance"),("hasPublicationInfo","pubinfo")):
            add(base,NP+link,iri(base+"#"+g),"head")
        stmt = base+"#claim"
        for key in ("subject","relation","object","condition","polarity","modality"):
            add(stmt,EX+key,literal(c[key]),"assertion")
        add(base+"#assertion",EX+"confidenceBasis",literal(c["confidence_basis"]),"provenance")
        add(base+"#assertion",EX+"support",literal(record["support"]),"provenance")
        for i, span in enumerate(spans, 1):
            anchor = base + "#observation-" + str(i)
            add(stmt, EX+"observation", iri(anchor), "provenance")
            add(anchor, EX+"supportingClause", literal(span["text"]), "provenance")
            add(anchor, PROV+"wasDerivedFrom", iri(base+"#e-"+quote(span["evidence"],safe="")), "provenance")
        for field, binding in record.get("bindings", {}).items():
            if field in ("subject", "relation", "object", "condition"):
                anchor = base+"#binding-"+field
                add(stmt, EX+"binding", iri(anchor), "provenance")
                add(anchor, EX+"field", literal(field), "provenance")
                add(anchor, EX+"text", literal(binding["text"]), "provenance")
                add(anchor, PROV+"wasDerivedFrom", iri(base+"#e-"+quote(binding["evidence"],safe="")), "provenance")
        if record["support"] == "inferred":
            add(base+"#assertion",EX+"derivation",literal(c["derivation"]),"provenance")
        for e in refs:
            evid = base+"#e-"+quote(e["id"],safe="")
            doc = base+"#d-"+quote(e["document"],safe="")
            add(base+"#assertion",PROV+"wasDerivedFrom",iri(evid),"provenance")
            add(evid,PROV+"wasDerivedFrom",iri(doc),"provenance")
            add(evid,EX+"quote",literal(e["quote"]),"provenance")
            add(evid,EX+"locator",literal(e["locator"]),"provenance")
            for k,v in metadata[e["document"]].items():
                if v is not None:
                    add(doc,EX+quote(k,safe=""),literal(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False)),"provenance")
        add(base,EX+"createdBy",literal(ctx.data["creator"]),"pubinfo")
        records.append(dict(record, iri=base, sources=refs, documents=metadata, creator=creator))
    if not records and not pending:
        ctx.issue("claims", "No candidates supplied")
    return {"claims.json":records, "nanopubs.nq":"\n".join(dict.fromkeys(quads)), "pending.json":pending}

if __name__ == "__main__":
    run(publish)
