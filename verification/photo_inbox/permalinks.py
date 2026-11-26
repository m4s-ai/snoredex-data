"""Record the permalinks of posts sent from the inbox in data/social.json (#646).

Reads the inbox's orders (the data folder, or its read-only share), adds every published permalink to
its printing's `instagramPosts`, `facebookPosts` or `threadsPosts`, and writes nothing else. A data PR
carries the change; it is opened and merged on green CI without asking again (AGENTS.md).
"""

from argparse import ArgumentParser
from pathlib import Path
import sys

from posting import published_links, write_json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from card_pages import PLATFORM_URLS, SOCIAL_FILE, checked_posts, read_social  # noqa: E402


def record(data_dir, root=ROOT):
    """Add the new permalinks; returns how many were added."""
    return add_links(root, published_links(data_dir))


def add_links(root, links):
    """Validate the complete result before replacing social.json; a retry adds each link only once."""
    by_item = read_social(root)
    added = 0
    for item_id, fields in links.items():
        row = by_item.get(item_id)
        if row is None:
            raise ValueError(f"{item_id}: posted, but not shared in {SOCIAL_FILE}")
        for field, urls in fields.items():
            if field not in PLATFORM_URLS:
                raise ValueError(f"Unexpected post field: {field}")
            new = list(dict.fromkeys(link for link in urls if link not in row.get(field, [])))
            if new:
                row[field] = row.get(field, []) + new
                added += len(new)
    if added:
        validate_links(by_item.values())
        write_json(root / SOCIAL_FILE, list(by_item.values()))
    return added


def validate_links(rows):
    used = set()
    for row in rows:
        for field, pattern in PLATFORM_URLS.items():
            checked_posts(row.get(field, []), used, pattern)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path, help="the inbox's data folder or its read-only share")
    args = parser.parse_args()
    print(f"{record(args.data_dir)} new permalinks recorded in {SOCIAL_FILE}")


if __name__ == "__main__":
    main()
