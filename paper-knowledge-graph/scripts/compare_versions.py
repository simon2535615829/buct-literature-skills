"""Compare two graph.json outputs by their declared stable IDs; retain both versions of changes."""
import argparse
import json
from pathlib import Path

def compare(old, new):
    def index(rows):
        items = {row['id']: row for row in rows}
        if len(items) != len(rows):
            raise ValueError('Duplicate graph identifier')
        return items
    result = {}
    for group in ('nodes', 'edges'):
        before, after = index(old[group]), index(new[group])
        result[group] = {
            'added': [after[k] for k in sorted(after.keys() - before.keys())],
            'removed': [before[k] for k in sorted(before.keys() - after.keys())],
            'changed': [{'id': k, 'before': before[k], 'after': after[k]}
                        for k in sorted(before.keys() & after.keys()) if before[k] != after[k]],
            'retained_ids': sorted(before.keys() & after.keys())
        }
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('previous', 'current', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    with args.output.open('x', encoding='utf8') as output:
        data = compare(json.loads(args.previous.read_bytes()), json.loads(args.current.read_bytes()))
        json.dump(data, output, ensure_ascii=False, indent=2)
        output.write('\n')

