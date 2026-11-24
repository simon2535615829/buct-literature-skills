"""Write a case result after validating its contract keys and named artifacts."""
import argparse
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def fields(contract):
    if isinstance(contract, list):
        if all(isinstance(x,str) for x in contract):
            return set(contract)
        if all(isinstance(x,dict) and isinstance(x.get("name"),str) for x in contract):
            return {x["name"] for x in contract if x.get("required",True)}
    if isinstance(contract, dict):
        required=contract.get("required")
        if isinstance(required,list) and all(isinstance(x,str) for x in required):
            return set(required)
        if isinstance(contract.get("properties"),dict):
            return set(contract["properties"])
        if "fields" in contract:
            return fields(contract["fields"])
        if not any(k in contract for k in ("type","schema","description","$ref","$schema","oneOf","allOf")):
            return set(contract)
    return None

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case",type=Path)
    ap.add_argument("draft",type=Path)
    ap.add_argument("output_dir",type=Path)
    ap.add_argument("--artifact",action="append",default=[],help="Existing artifact path relative to output_dir.")
    ap.add_argument("--require",action="append",default=[],help="Named mandatory field read from a prose contract.")
    a=ap.parse_args()
    try:
        case, draft=read(a.case),read(a.draft)
        if not isinstance(draft,dict) or "case_id" not in case or draft.get("case_id")!=case["case_id"]:
            raise ValueError("Missing or mismatched case_id")
        keys=fields(case.get("output_contract"))
        if keys is None and not a.require:
            raise ValueError("Read the case's contract and pass --require for its named fields")
        missing=(set(a.require)|(keys or set()))-draft.keys()
        if missing:
            raise ValueError("Missing contract fields: "+", ".join(sorted(missing)))
        home=a.output_dir.resolve()
        for rel in a.artifact:
            p=(home/rel).resolve()
            if Path(rel).is_absolute() or not p.is_relative_to(home) or not p.is_file() or not p.stat().st_size:
                raise ValueError("Missing, empty, or outside output: "+rel)
        home.mkdir(parents=True,exist_ok=True)
        result=json.dumps(draft,ensure_ascii=False,allow_nan=False,indent=2)+"\n"
        with NamedTemporaryFile(dir=home,mode="w",encoding="utf-8",delete=False) as tmp:
            tmp.write(result)
        os.replace(tmp.name,home/"result.json")
    except (OSError,ValueError,TypeError,KeyError) as e:
        ap.exit(2,f"Result not written: {e}\n")

if __name__=="__main__":
    main()
