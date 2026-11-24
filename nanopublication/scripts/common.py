"""Local review utilities, Python 3.9+ standard library."""
import json
import sys
from pathlib import Path


class Review:
    def __init__(self, spec, out):
        self.directory = spec.parent
        self.out = out
        self.issues = []
        self.evidence = {}
        self.data = json.loads(spec.read_text(encoding="utf-8-sig"))
        self.case_id = self.data["case_id"]
        if not self.case_id:
            raise ValueError("case_id missing")
        for e in self.data.get("evidence", []):
            key = e["id"]
            if not key or key in self.evidence:
                raise ValueError(f"Duplicate or empty evidence id: {key!r}")
            path = self.directory / e["file"]
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            first, last = e["lines"]
            excerpt = "\n".join(lines[first-1:last])
            if not (1 <= first <= last <= len(lines)) or not e["quote"].strip() or e["quote"] not in excerpt:
                raise ValueError(f"Evidence {key}: quote or line range does not match {e['file']}")
            if not e.get("locator"):
                raise ValueError(f"Evidence {key}: original page/section or field locator missing")
            self.evidence[key] = e

    def refs(self, keys):
        if not isinstance(keys, list) or not keys:
            raise ValueError("Expected at least one evidence ID")
        for key in keys:
            if key not in self.evidence:
                raise ValueError(f"Unknown evidence ID: {key}")
        return ", ".join(keys)

    def issue(self, where, why):
        self.issues.append({"where": where, "reason": why})

    def save(self, filename, value):
        self.out.mkdir(parents=True, exist_ok=True)
        p = self.out / filename
        if isinstance(value, str):
            p.write_text(value.rstrip() + "\n", encoding="utf-8")
        else:
            p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def finish(self, artifacts):
        for name, content in artifacts.items():
            self.save(name, content)
        self.save("review.json", {"case_id": self.case_id, "issues": self.issues,
                  "status": "needs_review" if self.issues else "checks_passed",
                  "artifacts": list(artifacts), "evidence": list(self.evidence.values())})


def run(process):
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python run.py INPUT.json NEW_OUTPUT_DIR")
    spec, out = map(Path, sys.argv[1:])
    try:
        if out.exists() and any(out.iterdir()):
            raise ValueError("Choose a fresh output directory")
        ctx = Review(spec, out)
        ctx.finish(process(ctx))
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        raise SystemExit(f"Input or output error: {exc}") from None
