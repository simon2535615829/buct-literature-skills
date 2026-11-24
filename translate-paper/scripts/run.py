import re
from collections import Counter

# Match whole scientific tokens before individual numbers. Differences are review flags.
LOCK = re.compile(r"\\\([^\\]*?\\\)|\$[^$\n]+\$|\\(?:cite|ref|eqref)\{[^}]+\}|\[\d+(?:\s*[,–-]\s*\d+)*\]")
def signatures(text):
    return Counter(re.sub(r"\s+", "", t).replace("−", "-").replace("µ","μ") for t in LOCK.findall(text))

def check_tokens(ctx, key, old, new, protected):
    a, b = signatures(old), signatures(new)
    if a != b:
        ctx.issue(key, f"Verify equations or references: removed {dict(a-b)}, added {dict(b-a)}")
    for term in protected:
        if old.count(term) != new.count(term):
            ctx.issue(key, f"Protected literal changed: {term}")

from common import run
from quantities import quantities
from alignment import occurs, flags, check_subjects


def translate(ctx):
    d = ctx.data
    blocks = d["source_blocks"]
    ids = {s["id"] for s in blocks}
    if not ids or len(ids) != len(blocks):
        raise ValueError("source_blocks needs unique paragraph IDs")
    translations = {}
    for item in d["translations"]:
        key = item["id"]
        if key not in ids or key in translations:
            raise ValueError(f"Unexpected or duplicate translated block: {key}")
        translations[key] = item["text"]
    text, aligned = [], []
    for b in blocks:
        key, original = b["id"], b["text"]
        new = translations.get(key, "")
        if not new.strip():
            ctx.issue(key, "Missing translation")
        check_tokens(ctx, key, original, new, b.get("protect", []))
        if Counter(quantities(original)) != Counter(quantities(new)):
            ctx.issue(key, "Verify measured values, comparison signs, units and their assignment to groups")
        for label in sorted(flags(original) ^ flags(new)):
            ctx.issue(key, f"Check {label} against original (lexical screening)")
        check_subjects(ctx, key, original, new, b.get("subject_pairs", {}))
        def source_present(term, entry):
            word = entry.get("source", term)
            forms = [word, *entry.get("source_forms", [])]
            # Regular variants are restricted to lowercase single-word terms and match whole words.
            if re.fullmatch(r"[a-z]{3,}", word):
                forms.extend([word + "s", word + ("d" if word.endswith("e") else "ed")])
            return any(occurs(form, original) for form in forms)

        defaults = [term for term, entry in d["glossary"].items()
                    if source_present(term, entry) and not entry.get("context_only")]
        for term in dict.fromkeys(defaults + b.get("terms", [])):
            item = d["glossary"][term]
            if not source_present(term, item):
                ctx.issue(key, f"Review glossary source form for {term} in this block")
            elif not occurs(item["target"], new):
                ctx.issue(key, f"Review glossary entry {term}: expected {item['target']}")
        aligned.append(dict(b, translation=new))
        text.extend([f"### {key} · {b['locator']}", original, new or "[待译]"])
    return {"bilingual.md": "\n\n".join(text), "alignment.json": aligned, "glossary.json": d["glossary"]}


if __name__ == "__main__":
    run(translate)
