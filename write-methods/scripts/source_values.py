"""Match parameter values and experimental counts to cited source sentences."""
import re
from decimal import Decimal
from verify_prose import NUMBER, RUN_ID, SCALES, canonical, names_in

COUNT_LABELS = {
    "replicates": (r"(?:重复(?:次数)?|重复实验|replicates?|repetitions?|repeat(?:ed|s)?)"
                   r"\s*(?:共|为|了|=|:)?\s*(\d+)\s*(?:次|times?)?|"
                   r"(\d+)\s*(?:次重复|replicates?\b|repetitions?\b)"),
    "samples": (r"(?:样本(?:数|量)|sample\s+size|samples?|(?<![A-Za-z])n(?=\s*=))\s*(?:为|共|=|:)?\s*(\d+)|"
                r"(\d+)\s*(?:个样本|份样本|samples?\b|participants?\b)"),
}
COUNT_PATTERNS = {k:re.compile(p,re.I) for k,p in COUNT_LABELS.items()}
BOUNDARY = re.compile(r"[;；。!！?？\n]|\.(?=\s+[A-Z]|$)")
NEGATIVE = re.compile(r"\b(?:not|never|planned|hypothetical)\b|未执行|未进行|计划", re.I)


def counts(text):
    return {(kind, int(a or b)) for kind, pattern in COUNT_PATTERNS.items()
            for a,b in pattern.findall(text)}


def same_scope(text, runs):
    source_runs = {s.casefold() for s in RUN_ID.findall(text)}
    return not source_runs or not runs or source_runs == runs


def observation_matches(parameter, obs, quote):
    labels = [parameter["id"], parameter["name"], *parameter.get("aliases", [])]
    unit = str(obs["unit"])
    dimension, expected = canonical(obs["value"], unit)
    equivalents = [u for u,(d,_) in SCALES.items() if d == dimension]
    if dimension in ("time", "mass", "volume", "length"):
        equivalents.extend(u.replace("µ", a) for u in list(equivalents) if "µ" in u for a in ("u","μ"))
    units = "|".join(map(re.escape, sorted(set(equivalents+[unit]),key=len,reverse=True)))
    value = (r"(" + NUMBER + r")\s*(" + units + r")(?![a-zA-Z0-9/])"
             if isinstance(expected, Decimal) else re.escape(str(expected)) + r"(?![A-Za-z0-9])")
    # Require a named field with its own value, not a matching number elsewhere in the log.
    connector = r"\s*(?:(?:was|is|of|at|为|等于|设为|设置为|[:=：])\s*)?"
    for clause in BOUNDARY.split(quote):
        if not same_scope(clause, {str(parameter["run"]).casefold()}):
            continue
        if obs.get("kind") == "observed" and NEGATIVE.search(clause):
            continue
        for start, end in names_in(clause,labels):
            after = re.match(connector + value, clause[end:], re.I if not unit else 0)
            before = re.search(r"(?<![A-Za-z0-9.])" + value + r"\s*$", clause[:start])
            for hit in (after,before):
                if hit and (not isinstance(expected, Decimal) or canonical(hit[1],hit[2]) == (dimension,expected)):
                    return True
    return False


def count_issues(text, excerpts, runs):
    wanted = counts(text)
    if not wanted:
        return []
    labels = re.compile(r'\b(?:group|arm|cohort)\s+[a-z0-9]+\b|[甲乙丙丁ABCD]组', re.I)
    groups = {m.casefold() for m in labels.findall(text)}
    supported = set()
    for excerpt in excerpts:
        source_runs = set()
        for statement in BOUNDARY.split(excerpt):
            explicit = {r.casefold() for r in RUN_ID.findall(statement)}
            if explicit:
                source_runs = explicit
            if runs and source_runs and source_runs != runs:
                continue
            source_groups = {m.casefold() for m in labels.findall(statement)}
            if groups and source_groups != groups:
                continue
            if same_scope(statement,runs) and not NEGATIVE.search(statement):
                supported.update(counts(statement))
    return [f"引文未证实{'重复次数' if kind=='replicates' else '样本数'} {n}"
            for kind,n in sorted(wanted - supported)]
