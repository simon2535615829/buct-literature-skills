"""Cross-language checks for glossary occurrences and explicit subject–clause pairs."""
import re
from collections import Counter
from quantities import quantities

SEMANTICS = {
    "negation": r"\b(?:not|never|without|no)\b|未|不|无|没有|并非",
    "qualification": r"\b(?:might|may|could|possibly|suggests?)\b|可能|或许|提示",
}
CLAUSES = re.compile(r"[；;。！？!?]|\.(?=\s|$)|\b(?:whereas|while)\b", re.I)


def occurs(term, text):
    if not term:
        return False
    left = r"(?<![A-Za-z0-9_])" if term[0].isascii() and term[0].isalnum() else ""
    right = r"(?![A-Za-z0-9_])" if term[-1].isascii() and term[-1].isalnum() else ""
    return bool(re.search(left + re.escape(term) + right, text, re.I))


def flags(text):
    return {label for label, pattern in SEMANTICS.items() if re.search(pattern, text, re.I)}


def clause_for(text, label, labels):
    starters = "|".join(re.escape(name) for name in labels)
    text = re.sub(r"(?:[,，]\s*(?:and\s+)?|\band\s+)(?=(?:" + starters + "))", ";", text, flags=re.I)
    hits = [part for part in CLAUSES.split(text) if occurs(label, part)]
    if len(hits) == 1 and sum(occurs(other, hits[0]) for other in labels) == 1:
        return hits[0]
    return None


def check_subjects(ctx, key, source, target, pairs):
    for original, translated in pairs.items():
        a = clause_for(source, original, pairs.keys())
        b = clause_for(target, translated, pairs.values())
        if not a or not b:
            ctx.issue(key, f"Align the clauses for {original} / {translated} manually")
        else:
            left = re.sub(re.escape(original), "", a, flags=re.I)
            right = re.sub(re.escape(translated), "", b, flags=re.I)
            if Counter(quantities(left)) != Counter(quantities(right)) or flags(left) != flags(right):
                ctx.issue(key, f"Verify quantities or qualification for {original} / {translated}: {a.strip()} → {b.strip()}")
