#!/usr/bin/env python3
"""Compare the end-product payloads of the working tree with a git revision, field by field.

Refactor-time tool: the reference is the payload state frozen at `REFERENCE_TAG`. Observational —
the revision is read with `git show`, its SQLite file goes to a temp directory outside the checkout.
Exit 0 = identical, 1 = differences, 2 = usage error or unreadable revision/path.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True  # importing database.py must not leave __pycache__ in the checkout
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from database import sqlite_dump  # noqa: E402

REFERENCE_TAG = "refactor-reference-20261109"
DETAIL_LIMIT = 40
VALUE_LIMIT = 100

# Paths not compared, per collection, as prefixes of "id" or "id/field/...". Every generated date and
# fingerprint in these payloads is derived from committed inputs or code constants, not the wall
# clock, so they stay compared. The one exception is a hash of the generator source itself:
VOLATILE = {
    # database.py:808 `"generator_sha256": file_hash(Path(__file__))` changes with any edit to
    # database.py, which is exactly what the refactor does; it carries no content.
    "sqlite": ["INSERT INTO \"metadata\" VALUES('generator_sha256',"],
}

HTML_BLOCKS = [("index.rows", "index.html", "data-rows", "rowId"),
               ("index.coverage", "index.html", "data-coverage", None),
               ("index.meta", "index.html", "data-meta", None),
               ("gallery.cards", "gallery.html", "gallery-data", "id")]
CATALOGUE_KEYS = {"items": "itemId", "assets": "assetId", "localSets": "localSetId",
                  "setEditions": "setEditionId", "works": "workId",
                  "localizations": "localizationId", "meta": None, "qualitySummary": None}


def git_bytes(rev: str, path: str) -> bytes:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    result = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, env=env, capture_output=True)
    if result.returncode:
        raise SystemExit(f"error: cannot read {rev}:{path}: {result.stderr.decode().strip()}")
    return result.stdout


def keyed(value, key):
    """A list keyed by `key`, or a whole object keyed by its top-level fields."""
    if key is None:
        return dict(value)
    records = {str(row[key]): row for row in value}
    assert len(records) == len(value), f"duplicate {key}"
    return records


def html_block(text: str, element_id: str):
    match = re.search(rf'<script type="application/json" id="{element_id}">(.*?)</script>', text, re.S)
    if not match:
        raise SystemExit(f"error: no <script id={element_id}> block")
    return json.loads(match.group(1))


def sqlite_lines(read) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "snoredex.sqlite"
        path.write_bytes(read("snoredex.sqlite"))
        return dict(Counter(sqlite_dump(path).splitlines()))  # line -> occurrences


def payloads(read) -> dict:
    texts = {name: read(name).decode("utf-8") for name in ("index.html", "gallery.html")}
    result = {name: keyed(html_block(texts[file], block), key) for name, file, block, key in HTML_BLOCKS}
    catalogue = json.loads(read("collector_catalogue.json"))
    for field, key in CATALOGUE_KEYS.items():
        result[f"catalogue.{field}"] = keyed(catalogue[field], key)
    result["sqlite"] = sqlite_lines(read)
    return result


def flatten(value, path: str) -> dict:
    if isinstance(value, dict) and value:
        return {k: v for key, item in value.items() for k, v in flatten(item, f"{path}/{key}").items()}
    if isinstance(value, list) and value:
        return {k: v for i, item in enumerate(value) for k, v in flatten(item, f"{path}[{i}]").items()}
    return {path: value}


def short(value, quote: bool = True) -> str:
    text = json.dumps(value, ensure_ascii=False) if quote else value
    return text if len(text) <= VALUE_LIMIT else text[:VALUE_LIMIT] + "..."


def changed_fields(record_id: str, old, new, skip: tuple) -> list[str]:
    old, new = flatten(old, record_id), flatten(new, record_id)
    paths = sorted(p for p in old.keys() | new.keys() if not p.startswith(skip))
    return [f"{short(p, False)}: {short(old.get(p))} -> {short(new.get(p))}"
            for p in paths if old.get(p) != new.get(p) or (p in old) != (p in new)]


def diff_collection(name: str, ref: dict, cur: dict) -> tuple[str, list[str], int]:
    """Summary line, detail lines and difference count for one collection."""
    skip = tuple(VOLATILE.get(name, ()))
    ref = {i: v for i, v in ref.items() if not i.startswith(skip)}
    cur = {i: v for i, v in cur.items() if not i.startswith(skip)}
    added, removed = sorted(cur.keys() - ref.keys()), sorted(ref.keys() - cur.keys())
    details = [f"{name} / {short(i, False)}: added" for i in added]
    details += [f"{name} / {short(i, False)}: removed" for i in removed]
    changed = 0
    for i in sorted(ref.keys() & cur.keys()):
        fields = changed_fields(i, ref[i], cur[i], skip)
        changed += bool(fields)
        details += [f"{name} / {line}" for line in fields]
    summary = (f"{name}: {len(ref)} in reference, {len(cur)} now; "
               f"{len(added)} added, {len(removed)} removed, {changed} changed")
    return summary, details, len(added) + len(removed) + changed


def report(ref: dict, cur: dict) -> int:
    total = 0
    for name in ref:
        summary, details, count = diff_collection(name, ref[name], cur[name])
        total += count
        print(summary)
        for line in details[:DETAIL_LIMIT]:
            print(f"  {line}")
        if len(details) > DETAIL_LIMIT:
            print(f"  ... and {len(details) - DETAIL_LIMIT} more")
    for name, paths in VOLATILE.items():
        print(f"not compared: {name} / {', '.join(paths)}")
    print(f"verdict: {'IDENTICAL' if not total else f'{total} differing ids'}")
    return 1 if total else 0


def selftest(ref: dict) -> int:
    """Mutate an in-memory copy of the working-tree payloads and expect exactly those changes."""
    cur = copy.deepcopy(ref)
    rows = cur["index.rows"]
    first, second = list(rows)[:2]
    rows[first]["selftestField"] = "changed"
    del rows[second]
    rows["selftest-added"] = {"rowId": "selftest-added"}
    _, details, count = diff_collection("index.rows", ref["index.rows"], rows)
    expected = ["index.rows / selftest-added: added", f"index.rows / {second}: removed",
                f'index.rows / {first}/selftestField: null -> "changed"']
    assert count == 3 and sorted(details) == sorted(expected), details
    print("selftest ok: one changed field, one removed id and one added id reported exactly")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", default=REFERENCE_TAG, help=f"git revision (default {REFERENCE_TAG})")
    parser.add_argument("--selftest", action="store_true", help="check the differ on mutated payloads")
    args = parser.parse_args()
    current = payloads(lambda path: (ROOT / path).read_bytes())
    if args.selftest:
        return selftest(current)
    return report(payloads(lambda path: git_bytes(args.ref, path)), current)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as stop:
        if isinstance(stop.code, str):
            print(stop.code, file=sys.stderr)
            sys.exit(2)
        raise
