"""Check scoped claims against the selected observations before drafting prose."""
from decimal import Decimal, InvalidOperation
import re

SCALES = {}
for dimension, units in {
    "time": {"ns": "1e-9", "µs": "1e-6", "ms": ".001", "s": "1", "min": "60", "h": "3600"},
    "length": {"nm": "1e-9", "µm": "1e-6", "mm": ".001", "cm": ".01", "m": "1"},
    "mass": {"µg": "1e-6", "mg": ".001", "g": "1", "kg": "1000"},
    "frequency": {"Hz": "1", "kHz": "1000", "MHz": "1e6"},
    "volume": {"µL": "1e-6", "mL": ".001", "L": "1"},
}.items():
    for unit, factor in units.items():
        SCALES[unit] = dimension, Decimal(factor)

NUMBER = r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?"
RUN_ID = re.compile(r"(?<![A-Za-z0-9])(?:R[-_]?\d+|run[-_ ]?\d+)(?![A-Za-z0-9])", re.I)
MARKER = re.compile(r"\{\{param:([^{}]+)\}\}")


def canonical(value, unit):
    unit = str(unit).strip().replace("μ", "µ")
    if unit in ("us", "um", "ug", "uL"):
        unit = "µ" + unit[1:]
    dimension, scale = SCALES.get(unit, (unit, Decimal(1)))
    try:
        return dimension, Decimal(str(value)) * scale
    except InvalidOperation:
        return dimension, str(value)


def names_in(text, names):
    found = []
    for name in filter(None, names):
        expr = re.escape(name)
        if name[0].isascii() and name[0].isalnum():
            expr = r"(?<![A-Za-z0-9])" + expr
        if name[-1].isascii() and name[-1].isalnum():
            expr += r"(?![A-Za-z0-9])"
        found.extend((m.start(), m.end()) for m in re.finditer(expr, text, re.I))
    return found


def inspect(ctx, raw, cited, facts, resolved, count_issues):
    from source_values import observation_matches
    draft = []
    preceding_runs = set()
    for clause in re.split(r"(?<=[。；;！？!\n])|(?<=\.)(?=\s+[A-Z])|(?<=[，,])(?=\s*(?:but\b|whereas\b|while\b|R[-_]?\d+|run[-_ ]?\d+))", raw, flags=re.I):
        mentions = []
        scoped_render = {}
        for key, p in facts.items():
            for start, end in names_in(clause, [p["name"], key, "{{param:" + key + "}}", *p.get("aliases", [])]):
                mentions.append((start, end, key))
        known_runs = {str(p["run"]) for p in facts.values()}
        runs = {r.casefold() for r in known_runs if names_in(clause, [r])}
        runs.update(m.group().casefold() for m in RUN_ID.finditer(clause))
        if runs:
            preceding_runs = runs
        reasons = count_issues(clause, [ctx.evidence[eid]["quote"] for eid in cited], preceding_runs)
        mentioned = {key for _, _, key in mentions}
        markers = set(MARKER.findall(clause))
        for key in sorted(mentioned):
            p = facts[key]
            peers = {other for other in mentioned if facts[other]["name"].casefold()==p["name"].casefold()
                     and str(facts[other]["run"]).casefold()==str(p["run"]).casefold()}
            if len(peers)>1:
                explicit = peers & markers
                supported = {other for other in peers if set(cited).intersection(
                    facts[other].get("resolved",{}).get("evidence",[]))}
                if explicit and key not in explicit:
                    continue
                if not explicit and len(supported)==1 and key not in supported:
                    continue
            if len(runs) == 1 and str(p["run"]).casefold() not in runs:
                # Parameters with the same display name may belong to different runs.
                if "{{param:" + key + "}}" not in clause and any(
                    facts[other]["name"] == p["name"] and str(facts[other]["run"]).casefold() in runs
                    for _, _, other in mentions):
                    continue
                reasons.append(key + " 的实验编号与记录不符")
            if len(runs) > 1:
                reasons.append(key + " 需要按运行分别核对")
            if "resolved" not in p:
                reasons.append(key + " 缺少已核定参数")
                continue
            selected = p["resolved"]
            target = canonical(selected["value"], selected["unit"])
            evidence = selected["evidence"]
            allowed = {target}
            config_only = re.search(r"\b(?:configured|config|default)\b|配置|默认",clause,re.I) and not re.search(
                r"\b(?:executed|observed|actual|used|override|overridden|applied|runtime|logged|measured|effective)\b|in effect|实际|实测|覆盖",clause,re.I)
            if config_only:
                configurations = [(o, eid) for o in p["observations"] if o["kind"] in ("default","configured")
                                  for eid in o["evidence"] if eid in cited and observation_matches(p,o,ctx.evidence[eid]["quote"])]
                if configurations:
                    allowed = {canonical(o["value"], o["unit"]) for o,eid in configurations}
                    evidence = [eid for o,eid in configurations]
                    if key in markers:
                        if len(allowed) != 1:
                            reasons.append(key+" 的配置值存在冲突")
                        else:
                            o=configurations[0][0]
                            scoped_render[key]=str(o["value"]),o["unit"]
                elif key in markers:
                    reasons.append(key+" 的配置值缺少配置来源")
            if not set(cited).intersection(evidence):
                reasons.append(key + " 未引用支持所选数值的记录")
            # Compare within the span of this parameter, stopping at the next named quantity.
            for start, end, field in mentions:
                if field != key or clause[start:end].startswith("{{"):
                    continue
                stop = min((a for a, _, other in mentions if a >= end and other != key), default=len(clause))
                segment = MARKER.sub("", clause[end:stop])
                units = set(SCALES) | {"us", "um", "ug", "uL", "μs", "μm", "μg", "μL", str(selected["unit"])}
                unit_expr = "|".join(map(re.escape, sorted(filter(None, units), key=len, reverse=True)))
                pattern = r"(?<![A-Za-z0-9.])(" + NUMBER + r")\s*(" + unit_expr + r")(?![A-Za-z0-9/])"
                segment = re.split(r"[，,]", segment, 1)[0]
                readings = re.findall(pattern, segment)
                leading = re.search(pattern + r"\s*$", clause[:start])
                if leading:
                    readings.append(leading.groups())
                for value, unit in readings:
                    actual = canonical(value, unit)
                    if actual not in allowed:
                        reasons.append(f"{key} 正文为 {value} {unit}，记录为 {selected['value']} {selected['unit']}")
        def render_marker(match):
            key=match.group(1)
            value=resolved[key]
            unit=facts[key].get("resolved",{}).get("unit")
            if key in scoped_render:
                number,unit=scoped_render[key]
                value=" ".join(part for part in (number,unit) if part)
            if unit and re.match(r"\s*"+re.escape(unit)+r"(?![A-Za-z0-9/])",clause[match.end():]):
                return scoped_render[key][0] if key in scoped_render else facts[key]["resolved"]["value"]
            return value
        rendered = MARKER.sub(render_marker, clause)
        if reasons:
            why = "；".join(dict.fromkeys(reasons))
            ctx.issue("正文", rendered.strip() + " — " + why)
            draft.append("[待核查：" + why + "]")
        else:
            draft.append(rendered)
    return "".join(draft)
