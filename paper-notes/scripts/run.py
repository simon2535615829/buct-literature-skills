from common import run
from numeric_evidence import verify, has_numeric_claim

def notes(ctx):
    data = ctx.data
    required = data["required_fields"]
    sections = {s: [] for s in data["sections"]}
    seen, covered = set(), set()
    cards = {}
    approved = {}
    pending = []
    aliases = {k.casefold(): v.casefold() for k,v in data.get("group_aliases", {}).items()}

    def hold(key, text, links, reasons):
        pending.append(dict(id=key,text=text,links=links,reasons=reasons))
        for reason in reasons:
            ctx.issue(key,reason)
    for n in data["notes"]:
        key = n["id"]
        if key in seen or n["section"] not in sections or not n["text"].strip():
            raise ValueError(f"Invalid note: {key}")
        seen.add(key)
        cards[key] = n
        if n.get("state") == "unreported":
            if not n.get("searched"):
                raise ValueError(f"{key}: document search scope missing")
            ref = "查阅范围 " + n["searched"]
            reasons = ["Numerical claim requires a cited source"] if has_numeric_claim(n["text"],aliases) else []
        else:
            ref = ctx.refs(n["evidence"])
            reasons = verify(n["text"], [ctx.evidence[e]["quote"] for e in n["evidence"]],aliases)
        if reasons:
            hold(key,n["text"],n.get("evidence",[]),reasons)
            continue
        covered.add(n["field"])
        approved[key]=n
        sections[n["section"]].append(f"- [{key}] {n['field']} · {n['text']} ({ref})")
    for f in sorted(set(required)-covered):
        ctx.issue(f, "Requested field has no note or documented gap")
    lines = []
    for index, summary in enumerate(data.get("summary", []), 1):
        if not summary["notes"] or set(summary["notes"])-seen:
            raise ValueError("Summary uses unknown or absent note IDs")
        blocked = [n for n in summary["notes"] if n not in approved]
        reasons = (["Referenced card requires review: "+", ".join(blocked)] if blocked else
                   verify(summary["text"],[cards[n]["text"] for n in summary["notes"]],aliases))
        if reasons:
            hold(f"summary[{index}]",summary["text"],summary["notes"],reasons)
            continue
        lines.append(summary["text"] + " ["+", ".join(summary["notes"])+"]")
    for section, items in sections.items():
        if not items:
            ctx.issue(section,"Declared section not covered")
        lines += ["## " + section, *items]
    for e in ctx.evidence.values():
        lines.append(f"> [{e['id']}] {e['locator']} — {e['quote']}")
    return {"notes.md":"\n\n".join(lines), "cards.json":list(approved.values()), "pending.json":pending}

if __name__ == "__main__":
    run(notes)
