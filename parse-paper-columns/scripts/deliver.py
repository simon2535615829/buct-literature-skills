"""Copy the original layout bytes and publish the case's file-list manifest."""
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path


def artifact_path(directory, name):
    path = (directory / name).resolve()
    if Path(name).is_absolute() or directory not in path.parents or path == directory / "result.json":
        raise ValueError(f"Expected an attachment path relative to the output directory: {name}")
    return path


def publish(args):
    case = json.loads(args.case.read_text(encoding="utf-8-sig"))
    manifest = json.loads(args.draft.read_text(encoding="utf-8-sig")) if args.draft else {}
    if not isinstance(manifest, dict) or manifest.get("case_id", case["case_id"]) != case["case_id"]:
        raise ValueError("Draft must be an object for the current case")
    names = [*args.attachments, args.layout_name]
    directory = args.output.resolve()
    paths = [artifact_path(directory, name) for name in names]
    if len(set(paths)) != len(names):
        raise ValueError("Attachment paths must be distinct")
    contract = case.get("output_contract", {})
    if isinstance(contract, dict):
        requested = contract.get("artifacts")
        if isinstance(requested, list) and requested and all(isinstance(n, str) for n in requested):
            if set(requested) != set(names):
                raise ValueError(f"Expected the case's attachment names: {requested}")
            names = requested
        if "properties" in contract or isinstance(contract.get("required"), list):
            required = contract.get("required", [])
        else:
            required = contract.keys()
        missing = set(required) - {"case_id", "artifacts"} - manifest.keys()
        if missing:
            raise ValueError(f"Provide remaining case fields in --draft: {sorted(missing)}")
    for file in [args.raw, *paths[:-1]]:
        if not file.is_file() or not file.stat().st_size:
            raise ValueError(f"Empty or missing attachment: {file}")
    manifest.update(case_id=case["case_id"], artifacts=names)
    data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    layout = paths[-1]
    layout.parent.mkdir(parents=True, exist_ok=True)
    if args.raw.resolve() != layout:
        with tempfile.TemporaryDirectory(dir=layout.parent) as staging:
            staged = Path(staging) / "layout"
            shutil.copyfile(args.raw, staged)
            os.replace(staged, layout)
    with tempfile.TemporaryDirectory(dir=directory) as staging:
        staged = Path(staging) / "manifest"
        staged.write_bytes(data)
        os.replace(staged, directory / "result.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("raw", type=Path, help="Original extract.py output")
    parser.add_argument("layout_name", help="Case-specified relative layout attachment name")
    parser.add_argument("attachments", nargs="*", help="Other completed attachment names, relative to output")
    parser.add_argument("--draft", type=Path, help="JSON object with any additional required case fields")
    parser.add_argument("--output", type=Path, default=Path("/app/output"))
    try:
        publish(parser.parse_args())
    except (OSError, KeyError, ValueError) as exc:
        parser.exit(2, f"Delivery failed: {exc}\n")
