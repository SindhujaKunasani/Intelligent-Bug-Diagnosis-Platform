"""Import normalized or source-specific CSV/JSON/JSONL bug datasets."""
import argparse
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core import Retrieval, clean_text

ALIASES = {
 'bug_id': ('bug_id', 'bugid', 'id', 'issue_key', 'issue_id', 'key'),
 'title': ('title', 'summary', 'short_desc', 'short_description'),
 'description': ('description', 'desc', 'body', 'issue_description'),
 'stack_trace': ('stack_trace', 'stacktrace', 'trace', 'exception'),
 'comments': ('comments', 'comment', 'discussion'),
 'resolution': ('resolution', 'resolution_text', 'fix', 'solution'),
 'status': ('status', 'state'),
 'url': ('url', 'issue_url', 'bug_url', 'link'),
 'source': ('source', 'project', 'repository'),
}


def normalize(raw, fallback_source):
    lower = {str(k).lower().strip(): v for k, v in raw.items()}
    output = {}
    for field, aliases in ALIASES.items():
        output[field] = next((clean_text(lower[a]) for a in aliases
                             if a in lower and lower[a] is not None), '')
    output['source'] = output['source'] or fallback_source
    return output


def load(path, source):
    if path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as fp:
            yield from (normalize(row, source) for row in csv.DictReader(fp))
    elif path.suffix.lower() == '.jsonl':
        with path.open(encoding='utf-8-sig') as fp:
            for line in fp:
                if line.strip():
                    yield normalize(json.loads(line), source)
    elif path.suffix.lower() == '.json':
        records = json.loads(path.read_text(encoding='utf-8-sig'))
        if isinstance(records, dict):
            records = records.get('bugs', records.get('issues', records.get('records', [])))
        yield from (normalize(row, source) for row in records)
    else:
        raise ValueError('Supported dataset formats: CSV, JSON, JSONL')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=Path)
    parser.add_argument('--source', required=True, help='e.g., Mozilla, Apache, Eclipse')
    args = parser.parse_args()
    records = list(load(args.file, args.source))
    records = [r for r in records if r['bug_id'] and (r['title'] or r['description'])]
    if not records:
        raise SystemExit('No records with bug_id and title/description found. Check CSV columns.')
    print(f'Loaded {len(records)} normalized defects; generating embeddings...')
    print(Retrieval().index(records))

if __name__ == '__main__':
    main()
