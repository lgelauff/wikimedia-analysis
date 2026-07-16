#!/usr/bin/env python3
"""Seed a rating set from a generic CSV.

CSV columns (header row required):
  ext_id        optional external id per item (e.g. dewiki:npov:5); enables dedupe
  source_text   REQUIRED — the statement shown primary (English)
  source_sub    optional — smaller secondary line (e.g. the German original)
  cand1_id, cand1_text, cand2_id, cand2_text, ...   candidate pairs (any count)

Adding a new set is just: write such a CSV and run
  uv run python seed.py --set-id my-set --name "My set" --k 3 data/my-set.csv
Re-running is idempotent when ext_id is present (existing items are skipped).
"""
import argparse
import csv
import json
import re
import sys

from app import create_app
from src.models import Item, RatingSet, db


def _candidate_cols(fieldnames: list[str]) -> list[int]:
    nums = set()
    for f in fieldnames:
        m = re.fullmatch(r'cand(\d+)_id', f)
        if m:
            nums.add(int(m.group(1)))
    return sorted(nums)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('csv', help='path to the items CSV')
    ap.add_argument('--set-id', required=True, help='slug for the set, e.g. de-en-npov')
    ap.add_argument('--name', required=True, help='human-readable set name')
    ap.add_argument('--k', type=int, default=3, help='target judgments per item (default 3)')
    ap.add_argument('--inactive', action='store_true', help='create the set as inactive')
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        rs = db.session.get(RatingSet, args.set_id)
        if rs is None:
            rs = RatingSet(id=args.set_id)
            db.session.add(rs)
        rs.name = args.name
        rs.k_target = args.k
        rs.is_active = not args.inactive

        with open(args.csv, newline='') as f:
            reader = csv.DictReader(f)
            cand_nums = _candidate_cols(reader.fieldnames or [])
            if 'source_text' not in (reader.fieldnames or []):
                sys.exit("CSV must have a 'source_text' column")
            added = skipped = 0
            for row in reader:
                ext_id = (row.get('ext_id') or '').strip() or None
                if ext_id and Item.query.filter_by(set_id=args.set_id, ext_id=ext_id).first():
                    skipped += 1
                    continue
                cands = []
                for n in cand_nums:
                    cid = (row.get(f'cand{n}_id') or '').strip()
                    ctext = (row.get(f'cand{n}_text') or '').strip()
                    if ctext:
                        cands.append({'id': cid or f'c{n}', 'text': ctext})
                db.session.add(Item(
                    set_id=args.set_id, ext_id=ext_id,
                    source_text=(row['source_text'] or '').strip(),
                    source_sub=(row.get('source_sub') or '').strip() or None,
                    candidates=json.dumps(cands, ensure_ascii=False),
                ))
                added += 1
        db.session.commit()
        print(f"set '{args.set_id}': +{added} items, {skipped} skipped (dupe). K={args.k}, active={rs.is_active}")


if __name__ == '__main__':
    main()
