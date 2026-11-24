"""Check reported quantities and sample counts against the cited text only."""
import re
from collections import defaultdict
from fractions import Fraction


UNITS = {}
def units(dimension, scale, aliases):
    for token in aliases.split():
        UNITS[token] = (dimension, Fraction(scale))


for dimension, scales in {
    "length": [("1000","km 千米"),("1","m 米"),(".01","cm 厘米"),(".001","mm 毫米"),("1e-6","μm µm um 微米"),("1e-9","nm 纳米")],
    "mass": [("1000","kg 千克"),("1","g 克"),(".001","mg 毫克"),("1e-6","μg µg ug 微克"),("1e-9","ng")],
    "volume": [("1","L l 升"),(".001","mL ml 毫升"),("1e-6","μL µL uL 微升")],
    "time": [("3600","h 小时"),("60","min 分钟"),("1","s 秒"),(".001","ms 毫秒")],
    "pressure": [("1","Pa"),("1000","kPa"),("1e6","MPa")],
    "frequency": [("1","Hz"),("1000","kHz"),("1e6","MHz")],
    "amount": [("1","mol"),(".001","mmol")],
    "temperature_C": [("1","°C ℃")], "percent":[("1","% ％")], "ppm":[("1","ppm")],
}.items():
    for scale, names in scales:
        units(dimension,scale,names)

UNIT = "(?:"+"|".join(map(re.escape,sorted(UNITS,key=len,reverse=True)))+")"
NUM = r"[+−-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+−-]?\d+)?"
OPERATORS = {"<=":"≤",">=":"≥","不超过":"≤","至少":"≥","至多":"≤","at most":"≤","at least":"≥",
             "低于":"<","高于":">","less than":"<","more than":">"}
OP = r"<=|>=|≤|≥|<|>|≈|~|不超过|至少|至多|低于|高于|(?i:at most|at least|less than|more than)"
MEASURE = re.compile(r"(?<![\d.])(?:(?P<op>"+OP+r")\s*)?(?P<a>"+NUM+r")"
                     r"(?:\s*(?P<join>±|–|至|到|(?<=\d)-(?=\d))\s*(?P<b>"+NUM+r"))?\s*(?P<u>"+UNIT+r")"
                     r"(?:\s*/\s*(?P<den>"+UNIT+r"))?(?![A-Za-z/²³^])")
COUNT = re.compile(r"(?:\b(?:sample\s+(?:size|count)|number\s+of\s+(?:participants|samples|subjects))\b\s*(?:was|is|of|=|:)?\s*"
                   r"|(?<![A-Za-z])n\s*[=:]\s*|样本(?:量|数)\s*(?:为|是|共|[=:：])?\s*)(?P<prefix>"+NUM+r")"
                   r"|(?P<suffix>"+NUM+r")\s*(?:participants\b|subjects\b|samples\b|patients\b|人(?:次)?|名(?:受试者|参与者|患者)|个样本|例(?:患者|病例)?)",re.I)
NAMED = re.compile(r"\b(?:group|arm|site|cohort|station)\s+(?:[A-Za-z0-9_-]+)\b|\b(?:north|south|east|west|control|treatment|placebo|treated)\b|[A-Za-z甲乙丙丁]组|对照组|实验组|治疗组|[南北东西]站",re.I)
DEFAULT = {"北站":"north","南站":"south","东站":"east","西站":"west","对照组":"control",
           "实验组":"treatment","治疗组":"treatment"}
SEP = re.compile(r"[;；。!?！？]|\.(?=\s+[A-Za-z]|$)|[,，](?!\d{3}\b)|\b(?:and|whereas|while|but)\b|而",re.I)


def value(raw):
    return Fraction(raw.replace(",","").replace("−","-"))


def entities(clause,aliases):
    labels=set()
    for label, canonical in aliases.items():
        if re.search((r"(?<![A-Za-z0-9_])" if label[0].isascii() else "")+re.escape(label)
                     +(r"(?![A-Za-z0-9_])" if label[-1].isascii() else ""),clause,re.I):
            labels.add(canonical)
            clause=re.sub(re.escape(label)," ",clause,flags=re.I)
    for match in NAMED.finditer(clause):
        name=match.group().casefold()
        if re.fullmatch(r"[a-z]组",name):
            name="group "+name[0]
        labels.add(DEFAULT.get(name,name))
    return labels


def simple_extract(text,aliases):
    facts=[]
    # Empty tails after commas (e.g. "North, n=8") inherit the group in the sentence.
    previous=set()
    for part in re.split("("+SEP.pattern+")",text,flags=re.I):
        if SEP.fullmatch(part):
            if part not in (",","，"):
                previous=set()
            continue
        labels=entities(part,aliases) or previous
        previous=labels
        for m in MEASURE.finditer(part):
            dim,mult=UNITS[m["u"]]
            if m["den"]:
                denom,scale=UNITS[m["den"]]
                dim+="/"+denom
                mult/=scale
            op=(m["op"] or "").casefold()
            join=m["join"]
            key=(dim,OPERATORS.get(op,op),value(m["a"])*mult,
                 "±" if join=="±" else "range" if join else "", value(m["b"])*mult if join else None)
            facts.append((frozenset(labels),key,m.group().strip()))
        for m in COUNT.finditer(part):
            raw=(m["prefix"] or m["suffix"]).rstrip(",")
            facts.append((frozenset(labels),("sample count",value(raw)),m.group().strip()))
    return facts


MARKER = re.compile(r"分别|\brespectively\b", re.I)
SENTENCE = re.compile(r"[;；。!?！？\n]|\.(?=\s|$)")
COMPACT_EN = re.compile(r"\b(groups|arms|sites|cohorts|stations)\s+([\w-]+)\s+and\s+([\w-]+)\b", re.I)
COMPACT_CN = re.compile(r"([A-Za-z甲乙丙丁])\s*[、和与]\s*([A-Za-z甲乙丙丁])\s*(?:两组|组)")
ITEM = (r"(?:(?:" + OP + r")\s*)?" + NUM + r"(?:\s*(?:±|–|至|到|(?<=\d)-(?=\d))\s*" + NUM + r")?"
        + r"(?:\s*" + UNIT + r"(?:\s*/\s*" + UNIT + r")?)?")
VALUES = re.compile(r"(?P<first>" + ITEM + r")\s*(?:和|与|及|、|[,，]|\band\b)\s*(?P<second>" + ITEM + r")")
COUNT_CONTEXT = re.compile(r"样本[量数]|sample (?:sizes?|counts?)", re.I)


def parallel_facts(sentence, aliases):
    # Expand shorthand labels before finding the two ends of the group list.
    sentence = COMPACT_EN.sub(lambda m: f"{m[1][:-1]} {m[2]} and {m[1][:-1]} {m[3]}", sentence)
    sentence = COMPACT_CN.sub(lambda m: f"{m[1]}组和{m[2]}组", sentence)
    names = [re.escape(name) for name in sorted(aliases, key=len, reverse=True) if name]
    names.append(NAMED.pattern)
    matches = list(re.finditer("|".join(names), sentence, re.I))
    if len(matches) != 2:
        raise ValueError("parallel list requires two explicit group names")
    a, b = matches
    if not re.fullmatch(r"\s*(?:and|和|与|及|、|,|，)\s*", sentence[a.end():b.start()], re.I):
        raise ValueError("group labels must form one ordered pair")
    groups = [entities(m.group(), aliases) for m in matches]
    if any(len(g) != 1 for g in groups) or groups[0] == groups[1]:
        raise ValueError("parallel list requires distinct, unambiguous groups")
    prefix = sentence[:a.start()]
    if MEASURE.search(prefix) or COUNT.search(prefix) or re.search(r"[,，、]\s*$", prefix):
        raise ValueError("separate other quantitative claims from the pair")
    tail = sentence[b.end():].strip()
    tail = re.sub(r"\s*[,，]?\s*\brespectively\b\s*$", "", tail, flags=re.I)
    start = re.search(r"(?:" + OP + "|" + NUM + ")", tail)
    pair = VALUES.fullmatch(tail[start.start():]) if start else None
    if not pair:
        raise ValueError("expected two values in the stated group order")
    values = [pair["first"].strip(), pair["second"].strip()]
    if COUNT_CONTEXT.search(tail[:start.start()] + " " + prefix):
        if not all(re.fullmatch(NUM, x) for x in values):
            raise ValueError("sample counts require two explicit counts")
        return [(frozenset(g), ("sample count", value(x)), x) for g, x in zip(groups, values)]
    parsed = [MEASURE.fullmatch(x) for x in values]
    unit_source = next((m for m in parsed if m), None)
    if unit_source is None:
        raise ValueError("parallel measurements need a unit")
    unit_text = unit_source["u"] + ("/" + unit_source["den"] if unit_source["den"] else "")
    facts = []
    for group, raw, match in zip(groups, values, parsed):
        scalar = raw if match else raw + " " + unit_text
        if not MEASURE.fullmatch(scalar):
            raise ValueError("unrecognized parallel measurement")
        _, key, _ = simple_extract(scalar, {})[0]
        facts.append((frozenset(group), key, scalar))
    if facts[0][1][0] != facts[1][1][0]:
        raise ValueError("parallel measurements use different dimensions")
    return facts


def parse_report(text, aliases):
    facts, errors = [], []
    for sentence in SENTENCE.split(text):
        if MARKER.search(sentence) and re.search(r"\d", sentence):
            try:
                facts.extend(parallel_facts(sentence, aliases))
            except ValueError as error:
                errors.append(str(error))
        else:
            facts.extend(simple_extract(sentence, aliases))
    return facts, errors


def has_numeric_claim(text, aliases):
    facts, errors = parse_report(text, aliases)
    return bool(facts or errors)



def verify(statement,sources,aliases):
    aliases=dict(aliases)
    # Learn short named cohorts from parallel clauses when the paper does not say "group".
    heads=set()
    for source in sources:
        for clause in SEP.split(source):
            match=re.match(r"\s*([A-Z][A-Za-z0-9_-]*)\s+(?:was|had|showed|recorded|yielded)\b",clause)
            if match and (MEASURE.search(clause) or COUNT.search(clause)):
                heads.add(match[1].casefold())
    if len(heads)>1:
        for head in heads:
            if not NAMED.fullmatch(head):
                aliases.setdefault(head,head)
    evidence=defaultdict(set)
    for src in sources:
        for groups,key,_ in parse_report(src,aliases)[0]:
            evidence[key].add(groups)
    wanted,reasons=parse_report(statement,aliases)
    for groups,key,raw in wanted:
        found=evidence.get(key,set())
        if key[0]=="sample count" and (key[1].denominator!=1 or key[1]<0):
            reasons.append(f"{raw}: expected a nonnegative whole sample count")
        elif len(groups)>1 or (groups and groups not in found):
            reasons.append(f"{raw}: check assignment to {', '.join(sorted(groups))}")
        elif not found:
            reasons.append(f"{raw}: no matching {key[0]} in cited source")
        elif not groups and frozenset() not in found and len({g for choices in evidence.values() for g in choices if g})>1:
            reasons.append(f"{raw}: specify which reported group this refers to")
    return list(dict.fromkeys(reasons))
