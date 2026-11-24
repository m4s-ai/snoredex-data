"""Record the permalinks of posts sent from the inbox in data/social.json (#646).

Reads the inbox's orders (the data folder, or its read-only share), adds every published permalink to
its printing's `instagramPosts`, `facebookPosts` or `threadsPosts`, and writes nothing else. A data PR
carries the change; it is opened and merged on green CI without asking again (AGENTS.md).
"""

from argparse import ArgumentParser
import json
from pathlib import Path
import sys

from posting import published_links

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from card_pages import SOCIAL_FILE, read_social  # noqa: E402


def record(data_dir, root=ROOT):
    """Add the new permalinks; returns how many were added."""
    path = root / SOCIAL_FILE
    rows = json.loads(path.read_text(encoding="utf-8"))
    by_item = {row["itemId"]: row for row in rows}
    added = 0
    for item_id, fields in published_links(data_dir).items():
        row = by_item.get(item_id)
        if row is None:
            raise ValueError(f"{item_id}: posted, but not shared in {SOCIAL_FILE}")
        for field, links in fields.items():
            new = [link for link in links if link not in row.get(field, [])]
            if new:
                row[field] = row.get(field, []) + new
                added += len(new)
    if added:
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        read_social(root)  # the result must pass the same validation the build applies
    return added


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path, help="the inbox's data folder or its read-only share")
    args = parser.parse_args()
    print(f"{record(args.data_dir)} new permalinks recorded in {SOCIAL_FILE}")


if __name__ == "__main__":
    main()
