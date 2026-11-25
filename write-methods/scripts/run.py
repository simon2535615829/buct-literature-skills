from common import run
from verify_prose import canonical, inspect
from source_values import observation_matches, count_issues

def methods(ctx):
    d=ctx.data
    facts, resolved={},{}
    for p in d["parameters"]:
        key=p["id"]
        if key in facts:
            raise ValueError(f"Duplicate parameter {key}")
        facts[key]=p
        p.pop("resolved", None)
        obs=p["observations"]
        for o in obs:
            if o.get("unit") is None:
                o["unit"] = ""
            ctx.refs(o["evidence"])
        pairs={(str(o["value"]),o["unit"]) for o in obs}
        decision=p.get("resolution",{})
        if decision.get("unit") is None:
            decision["unit"] = ""
        chosen=(str(decision.get("chosen")),decision.get("unit"))
        selected_obs = [o for o in obs if (str(o["value"]),o["unit"])==chosen]
        linked = {eid for o in selected_obs for eid in o["evidence"]}
        if obs and all(o["kind"]=="default" for o in obs) and p.get("purpose")!="configuration":
            ctx.issue(key,"Only a code default is documented; the executed setting needs a run record")
            resolved[key]="[待确认 "+key+"]"
            continue
        if obs and len({canonical(o["value"], o["unit"]) for o in obs}) == 1:
            preferred = next((o for o in obs if o["kind"] == "observed"), obs[0])
            picked = str(preferred["value"]), preferred["unit"]
            basis=", ".join(sorted({o["kind"] for o in obs}))
        elif (chosen in pairs and decision.get("reason") and decision.get("evidence")
              and linked.intersection(decision["evidence"])):
            ctx.refs(decision["evidence"])
            picked=chosen
            basis=decision["reason"]
        else:
            ctx.issue(key,"Unresolved conflicting or missing observations: "+repr(sorted(pairs)))
            resolved[key]="[待确认 "+key+"]"
            continue
        target = canonical(*picked)
        matching = [o for o in obs if canonical(o["value"],o["unit"]) == target]
        relevant = {eid for o in matching for eid in o["evidence"]}
        if len({canonical(o["value"], o["unit"]) for o in obs}) > 1:
            relevant.intersection_update(decision["evidence"])
        verified = sorted({eid for o in matching for eid in o["evidence"] if eid in relevant
                           and observation_matches(p, o, ctx.evidence[eid]["quote"])})
        if not verified:
            ctx.issue(key, "选定的参数值与运行范围无法在所引原句中核实，见 " + ", ".join(sorted(relevant)))
            resolved[key] = "[待确认 " + key + "]"
            continue
        resolved[key]=" ".join(x for x in picked if x)
        p["resolved"]={"value":picked[0],"unit":picked[1],"basis":basis,"evidence":verified}
    lines=[]
    for s in d["sections"]:
        lines.append("## "+s["heading"])
        for para in s["prose"]:
            support=ctx.refs(para["evidence"])
            content=inspect(ctx, para["text"], para["evidence"], facts, resolved, count_issues)
            lines.append(content+" ["+support+"]")
    lines.append("## 参数与运行范围")
    for key,p in facts.items():
        lines.append(f"- {p['run']} / {p['stage']} / {p['name']} = {resolved[key]}")
    for gap in d.get("gaps",[]):
        ctx.issue(gap["field"],gap["reason"])
    if ctx.issues:
        lines.append("## 待确认")
        lines.extend("- "+x["where"]+" — "+x["reason"] for x in ctx.issues)
    return {"methods.md":"\n\n".join(lines),"parameter-ledger.json":list(facts.values()),
            "source-map.json":d["sections"]}

if __name__ == "__main__":
    run(methods)
