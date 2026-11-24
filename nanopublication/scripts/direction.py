"""Validate explicit pairwise comparisons in the cited excerpts."""
import re

OP = re.compile(r"\b(lower|less|smaller|shorter|fewer|slower|worse|higher|greater|more|larger|longer|faster|better)\b(?=[^.,;:!?]{0,42}?\bthan\b)|低于|小于|少于|短于|慢于|劣于|高于|大于|多于|长于|快于|优于|[<>]", re.I)
LOW = {"lower", "less", "smaller", "shorter", "fewer", "slower", "worse", "低于", "小于", "少于", "短于", "慢于", "劣于", "<"}
NEG = re.compile(r"\b(?:not|never|no)\b|未|没有|并非|(?<!并)不", re.I)


def signs(phrase):
    return {(-1 if m.group().lower() in LOW else 1) for m in OP.finditer(phrase)}


def entity_pattern(label):
    label = label.strip()
    left = r"(?<![a-zA-Z0-9])" if label[0].isascii() and label[0].isalnum() else ""
    right = r"(?![a-zA-Z0-9])" if label[-1].isascii() and label[-1].isalnum() else ""
    return re.compile(left + re.escape(label) + right)


def check(claim, excerpts):
    relation = claim["relation"]
    desired = signs(relation)
    if not desired or claim.get("support", "direct") != "direct":
        return None
    if len(desired) != 1 or NEG.search(relation) or claim["polarity"].lower() not in ("positive", "affirmative", "肯定", "正向"):
        return "比较关系含否定或有多种解释，请核对原句的比较方向和极性"
    observed = set()
    uncertain = False
    entities = [entity_pattern(claim[k]) for k in ("subject", "object")]
    for excerpt in excerpts:
        for clause in re.split(r"[;；。!！?？\n]|\.(?=\s|$)", excerpt):
            pairs = [list(pattern.finditer(clause)) for pattern in entities]
            if not all(pairs):
                continue
            if any(len(matches) != 1 for matches in pairs):
                uncertain = True
                continue
            a, b = (v[0] for v in pairs)
            first, last = sorted((a, b), key=lambda m: m.start())
            middle = clause[first.end():last.start()]
            direction = signs(middle)
            if not direction:
                continue
            if NEG.search(middle) or re.search(r"\b(and|but|whereas|while)\b|[，,]|而|但是", middle, re.I):
                uncertain = True
                continue
            observed.update(direction if first == a else {-s for s in direction})
    if uncertain or observed != desired:
        return "核对比较双方与方向：直接引用无法唯一支持所写的主语、比较关系和宾语"
    return None
