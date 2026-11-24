"""Bind a direct claim to observations made under the stated conditions."""
import re
import unicodedata
from decimal import Decimal
from direction import check, entity_pattern, signs, NEG, OP

TEMP = re.compile(r"(?<![A-Za-z0-9.])([+\-−]?\d+(?:\.\d+)?)\s*°\s*([cf])(?![a-z])", re.I)
CLAUSE = re.compile(r"[;；。!！?？\n]|\.(?=\s|$)|\b(?:whereas|while|but)\b|而在", re.I)
NON_POINT = re.compile(r"(?:[<>≤≥~≈]|\b(?:above|below|over|under|at least|at most)|(?:高于|低于|不少于|不超过)|\d\s*(?:[–—-]|to|至|到))\s*[+−-]?\d+(?:\.\d+)?\s*°\s*[cf]", re.I)
GENERIC = {"reported comparison", "reported observation", "reported experiment"}

def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())

def temperatures(text):
    return {(Decimal(m[1].replace("−","-")),m[2].lower()) for m in TEMP.finditer(text)}

def relation_matches(relation, source):
    # Retain the quantity being compared, e.g. "drift" in "had less drift than".
    fillers = {"had","has","have","was","is","were","are","a","an","the","than","at","of","in","to"}
    terms = [w for w in re.findall(r"[a-z]+", OP.sub(" ", normalize(relation))) if w not in fillers]
    return all(re.search(r"\b"+re.escape(w)+r"(?:s|ed|ing)?\b", source) for w in terms)


def select_support(claim, refs):
    if claim.get("support", "direct") != "direct":
        return [], None
    condition = normalize(claim["condition"])
    expected = temperatures(condition)
    remaining = TEMP.sub(" ", condition)
    qualifiers = [q.strip() for q in re.split(r"[,，;；]",remaining) if q.strip() and q.strip() not in GENERIC | {"at","在","时","在 时","下","在 下"}]
    entities = [entity_pattern(claim[k]) for k in ("subject","object")]
    comparison = bool(signs(claim["relation"]))
    bindings = claim.get("bindings", {})
    accepted = []
    for ref in refs:
        matched_in_excerpt = False
        for raw in CLAUSE.split(ref["quote"]):
            raw = raw.strip(" ,，")
            text = normalize(raw)
            if not all(pattern.search(raw) for pattern in entities):
                continue
            if comparison and (not signs(raw) or not relation_matches(claim["relation"], text)):
                continue
            temps = temperatures(text)
            if expected and NON_POINT.search(text):
                continue
            if temps != expected or not all(entity_pattern(q).search(text) for q in qualifiers):
                # A contrary continuation without its own condition is ambiguous.
                if matched_in_excerpt and expected and not temps and comparison and check(claim,[raw]):
                    return [], "Unqualified continuation may contradict the scoped observation"
                continue
            if comparison:
                issue = check(claim,[raw])
                if issue:
                    return [], issue
            else:
                relation = bindings.get("relation",{}).get("text",claim["relation"])
                if not entity_pattern(normalize(relation)).search(text) or bool(NEG.search(text)) != bool(NEG.search(normalize(relation))):
                    continue
            if bindings and not all(
                bindings[k]["evidence"] == ref["id"] and bindings[k]["text"] in raw
                for k in ("subject","relation","object","condition")
            ):
                continue
            matched_in_excerpt = True
            accepted.append({"evidence":ref["id"],"locator":ref["locator"],"text":raw})
    if not accepted:
        return [], "No single cited observation establishes these entities, relation and conditions together"
    return accepted, None

