
#!/usr/bin/env python3
"""Plan, resume and verify Snoredex gallery work without remote mutations."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check import carries_location, dump

ROOT = Path(__file__).resolve().parents[1]
PHOTO = "verification/specimens/"
IMAGES = "data/images.json"
REGISTER = "verification/specimens.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def index(rows, key):
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), f"Duplicate {key}")
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def local_path(root, path, prefix):
    target = (root / path).resolve()
    require(path.startswith(prefix) and target.is_relative_to(root / prefix), f"Unsafe path: {path}")
    return target


def save(path, data):
    if path.is_file() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Each destination is replaced atomically. An interrupted multi-file apply is replayable.
    import tempfile

    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp:
        pending = Path(temp.name)
        temp.write(data)
    try:
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def write(path, value):
    save(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def read_optional(path, default):
    return read(path) if path.exists() else default


def gallery_cards(root):
    html = (root / "gallery.html").read_text(encoding="utf-8")
    return json.loads(re.search(r'<script\b[^>]*\bid="gallery-data"[^>]*>(.*?)</script>', html, re.S)[1])


def gallery_inventory(root):
    cards = index(gallery_cards(root), "id")
    active = {row["itemId"] for row in read(root / "data/printings.json")["printings"] if row["active"]}
    hypotheses = set(index(read(root / IMAGES)["placeholders"], "id"))
    require(set(cards) == active | hypotheses, "Generated gallery is stale. Regenerate before inventory.")
    require(not active & hypotheses, "A hypothesis overlaps an active printing.")
    return cards


def freeze(root, output, ids, number):
    require(not output.exists(), f"Target list already exists: {output}")
    cards = gallery_inventory(root)
    require(0 < len(ids) <= 20 and len(set(ids)) == len(ids), "Choose 1 to 20 distinct item IDs.")
    targets = []
    for key in ids:
        card = cards[key]
        require(card["kind"] != "research-placeholder" and not card["preview"], f"Not an active image gap: {key}")
        targets.append({"itemId": key, "collectorNumber": card["number"].split("/")[0]})
    write(output, {"round": number, "basis": git(root, "rev-parse", "HEAD").decode().strip(), "targets": targets})


def round_inputs(root, folder):
    frozen = read(folder / "targets.json")
    targets = index(frozen["targets"], "itemId")
    source_review = read_optional(folder / "source-review.json", {"targets": []})
    review = index(source_review["targets"], "itemId")
    items = index(read(root / "data/printings.json")["printings"], "itemId")
    checks = [0 < len(targets) <= 20, review.keys() <= targets.keys(),
              all(items[key]["active"] for key in targets)]
    require(all(checks), "Round targets or decisions do not match the active inventory.")
    return frozen["round"], targets, review, items


def archive_files(photos, tip):
    entries = git(photos, "ls-tree", "-rz", tip, "--", PHOTO).decode().split("\0")
    files = {}
    for entry in filter(None, entries):
        info, path = entry.split("\t", 1)
        mode, kind, oid = info.split()
        require(kind == "blob" and mode != "120000", f"Non-file in photo archive: {path}")
        files[path] = oid
    return files


def photo_states(photos, intake):
    if not intake:
        return {}
    remote = git(photos, "rev-parse", "refs/remotes/origin/main").decode().strip()
    files = archive_files(photos, remote)
    states = {}
    for row in intake:
        source = row["photoRepositoryPath"]
        path = local_path(photos, source, PHOTO)
        require(path.name == row["photograph"], f"Inconsistent archive filename: {source}")
        expected = row["photoRepositorySha256"]
        if source in files:
            require(list(files.values()).count(files[source]) == 1, f"Archive contains duplicate original bytes: {source}")
            data = git(photos, "show", f"{remote}:{source}")
            require(digest(data) == expected and not carries_location(data), f"Archive hash or GPS conflict: {source}")
            states[source] = "archived"
        elif path.exists():
            require(digest(path.read_bytes()) == expected, f"Local archive collision: {source}")
            states[source] = "local-only"
        else:
            states[source] = "missing"
    return states


def verify_bytes(root, path, expected, prefix):
    data = local_path(root, path, prefix).read_bytes()
    require(digest(data) == expected.removeprefix("sha256:"), f"SHA-256 mismatch: {path}")


def verify_round_files(root, row, asset):
    images = row["images"]
    widths = [size["width"] for size in images]
    require(len(widths) == 3 and widths[:2] == [240, 480] and 600 <= widths[2] <= 1200,
            f"Invalid responsive widths: {row['itemId']}")
    for size in images:
        verify_bytes(root, size["path"], size["sha256"], "images/gallery/")
    if asset and asset.get("preview"):
        local_path(root, asset["preview"], "images/previews/").stat()


def planned_associations(intake, prior, register):
    records = {}
    for row in intake:
        for key in row["itemIds"]:
            require(key not in records, f"Repeated intake target: {key}")
            records[key] = {"source": row["photoRepositoryPath"], "scope": row["scope"],
                            "mediaKind": row["mediaKind"]}
    for row in prior:
        spec = register[row["specimenId"]]
        records[row["itemId"]] = {"source": PHOTO + spec["photograph"], "scope": "representative"}
    return records


def confirmed_associations(accepted, planned, current):
    return {key for key, row in (planned | accepted).items() if key in current
            and all(current[key][field] == value for field, value in row.items()
                    if field in ("source", "scope", "mediaKind"))}


def read_round(root, folder, photos):
    number, targets, review, _ = round_inputs(root, folder)
    plan = read_optional(folder / "intake.json", {"intake": []})
    intake = plan["intake"]
    archived = photo_states(photos, intake) if photos else {}
    accepted = index(read_optional(folder / "accepted.json", {"targets": []})["targets"], "itemId")
    canonical = read(root / IMAGES)
    current = index(canonical["galleryImages"], "itemId")
    require(accepted.keys() <= targets.keys(), "Accepted IDs fall outside the frozen round.")
    gaps = {key: row["reason"] for key, row in review.items() if row["decision"] == "needs-image"}
    require(not accepted.keys() & gaps.keys(), "A target is accepted and also marked as a gap.")
    registry = index(read(root / REGISTER)["specimens"], "specimenId")
    planned = planned_associations(intake, plan.get("reusedSpecimens", []), registry)
    require(planned.keys() <= targets.keys(), "Planned IDs fall outside the frozen round.")
    integrated = confirmed_associations(accepted, planned, current)
    require(not integrated & gaps.keys(), "A documented gap has an applied image.")
    return {
        "round": number, "targetCount": len(targets), "galleryAssociations": len(integrated),
        "gaps": gaps, "originals": archived, "intakeCount": len(intake),
        "pending": sorted(targets.keys() - integrated - gaps.keys()),
        "conflicts": sorted((targets.keys() & current.keys()) - integrated),
    }


def verify_round(root, folder, photos):
    result = read_round(root, folder, photos)
    require((folder / "accepted.json").is_file(), "Apply the reviewed round to produce its acceptance record.")
    require(not (result["pending"] or result["conflicts"]), "The round has pending targets or conflicts.")
    require(all(state == "archived" for state in result["originals"].values()), "Originals are pending upload.")
    _, targets, _, items = round_inputs(root, folder)
    document = read(root / IMAGES)
    assets = {asset["path"]: asset for asset in document["assets"]}
    register = index(read(root / REGISTER)["specimens"], "specimenId")
    gallery = index(document["galleryImages"], "itemId")
    intake = read_optional(folder / "intake.json", {"intake": []})["intake"]
    for source in intake:
        verify_bytes(root, source["previewPath"], source["previewSha256"], "images/previews/")
    for key in targets.keys() - result["gaps"].keys():
        row = gallery[key]
        spec = register.get(Path(row["source"]).stem)
        if row["source"].startswith(PHOTO):
            require(spec and spec["language"] == items[key]["setEditionId"].split(":")[-2], f"Source language: {key}")
            require(photos, "Supply --photos to verify specimen originals.")
            verify_bytes(photos, row["source"], spec["photographSha256"], PHOTO)
        verify_round_files(root, row, assets.get(row["source"]))
    return result


def check_command(root, *args):
    subprocess.run([sys.executable, *map(str, args)], cwd=root, check=True)


def file_artifact(root, artifact):
    check_command(root, "scripts/publish.py", "--out", artifact)
    check_command(root, "scripts/publish.py", "--out", artifact, "--verify")
    for path in artifact.rglob("*"):
        if path.is_file() and path.suffix != ".md" and path.name != ".nojekyll":
            require(digest(path.read_bytes()) == digest((root / path.relative_to(artifact)).read_bytes()),
                    f"Artifact differs from checkout: {path.name}")
    for db in artifact.glob("*.sqlite"):
        with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as connection:
            require(connection.execute("PRAGMA quick_check").fetchone() == ("ok",), f"Database corrupt: {db.name}")


def preview_paths(root):
    paths = {asset["preview"] for asset in read(root / IMAGES)["assets"] if asset.get("preview")}
    return [local_path(root, path, "images/previews/") for path in sorted(paths)]


def gallery_files(root, cards):
    from PIL import Image

    outputs = {r["path"]: r for card in cards.values() for r in card.get("imageSizes", [])}
    for path, row in outputs.items():
        verify_bytes(root, path, row["sha256"], "images/gallery/")
        with Image.open(local_path(root, path, "images/gallery/")) as image:
            require(image.size == (row["width"], row["height"]) and image.format == "WEBP",
                    f"Incorrect rendition size or type: {path}")
            image.verify()
    previews = preview_paths(root)
    for path in previews:
        with Image.open(path) as image:
            expected = {".png": "PNG", ".jpg": "JPEG"}.get(path.suffix.lower())
            require(0 < image.width <= 360 and image.format == expected, f"Incorrect preview: {path}")
            image.verify()
    return {"renditions": len(outputs), "previews": len(previews)}


def verification_basis(root):
    paths = sorted((root / "data").glob("*.json"))
    paths += [root / name for name in ("gallery.html", "index.html", "collector_catalogue.json",
                                       "snoredex.sqlite", "snoredex-tracker-template.sqlite", REGISTER)]
    paths += sorted(p for p in (root / "site").rglob("*") if p.is_file())
    paths += preview_paths(root)
    return {"head": git(root, "rev-parse", "HEAD").decode().strip(),
            "sha256": {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in paths}}


def round_fingerprint(folder):
    names = ("targets.json", "source-review.json", "accepted.json", "intake.json",
             "preparation.json", "registry-additions.json")
    return {name: digest((folder / name).read_bytes()) for name in names if (folder / name).exists()}


def current_verification(args, result):
    if not args.report:
        return
    report = read(args.report)
    result["verificationCurrent"] = (
        report["roundFiles"] == round_fingerprint(args.round_dir) and
        report["basis"] == verification_basis(args.repo) and
        not (result["pending"] or result["conflicts"])
    )


def verify_site(args):
    from gallery_browser import run

    root = args.repo
    before = verification_basis(root)
    cards = gallery_inventory(root)
    if args.command == "verify":
        round_files = round_fingerprint(args.round_dir)
        state = verify_round(root, args.round_dir, args.photos)
        keys = index(read(args.round_dir / "targets.json")["targets"], "itemId")
    else:
        state = {}
        keys = cards
    files = gallery_files(root, cards)
    check_command(root, "scripts/regen.py", "--check")
    check_command(root, "scripts/check.py", "--photos", args.photos)
    artifact = root / "_site-gallery-review"
    file_artifact(root, artifact)
    browser = run(artifact, cards, keys, all_groups=args.command == "audit")
    require(verification_basis(root) == before, "Inputs changed during validation. Repeat on a stable checkout.")
    result = {"basis": before, "roundState": state, "browser": browser, "files": files,
              "photoArchive": git(args.photos, "rev-parse", "refs/remotes/origin/main").decode().strip(),
              "checks": ["regeneration", "original-sha256-and-gps", "artifact-allowlist-and-bytes", "sqlite-quick-check"]}
    if args.command == "verify":
        require(round_fingerprint(args.round_dir) == round_files, "Round decisions changed during validation.")
        result["roundFiles"] = round_files
    else:
        check_command(root, "verification/test_site.py")
        from gallery_browser import review_packet

        review_packet(args.report.parent, cards, artifact)
        result.update(visualAcceptance="pending", physical=sum(c["kind"] != "research-placeholder" for c in cards.values()),
                      hypotheses=[c["id"] for c in cards.values() if c["kind"] == "research-placeholder"],
                      imageNeeds=[c["id"] for c in cards.values() if not c["preview"]])
    require(verification_basis(root) == before, "Inputs changed during validation. Repeat on a stable checkout.")
    write(args.report, result)


def sign_off(args):
    report = read(args.report)
    require(report["visualAcceptance"] == "pending", "Expected a technical audit report awaiting visual review.")
    require(report["basis"] == verification_basis(args.repo), "The technical audit refers to an older state.")
    visual = read(args.review)
    from gallery_browser import by_group

    cards = gallery_inventory(args.repo)
    require(gallery_files(args.repo, cards) == report["files"], "Gallery files differ from the audited inventory.")
    groups = by_group(cards)
    require(set(visual["reviewedGroups"]) == set(groups), "Review must cover every artwork group.")
    require(set(visual["imageNeeds"]) == set(report["imageNeeds"]), "Explain every remaining image need.")
    require(all(reason.strip() for reason in visual["imageNeeds"].values()), "Empty reason for an image need.")
    require(visual["reviewer"].strip() and visual["checkedAt"].strip(), "Record who reviewed the gallery and when.")
    require(visual["basis"] == report["basis"], "Visual review refers to a different technical audit.")
    report.update(visualAcceptance="recorded", visualReview=visual)
    write(args.out, report)


def add_render_parser(commands):
    sub = commands.add_parser("render")
    sub.add_argument("round_dir", type=Path)
    sub.add_argument("--candidate", required=True)
    sub.add_argument("--specimen", required=True)
    sub.add_argument("--source", type=Path, required=True)
    sub.add_argument("--corners", nargs=8, type=float, metavar="PX",
                     help="Native pixel coordinates: top left, top right, bottom right, bottom left")


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repo", type=Path, default=ROOT, help="Checkout to inspect, defaults to this repository")
    commands = cli.add_subparsers(dest="command", required=True)
    for name in ("freeze", "status", "check", "apply", "verify", "audit"):
        sub = commands.add_parser(name)
        if name not in ("freeze", "audit"):
            sub.add_argument("round_dir", type=Path)
        if name != "freeze":
            sub.add_argument("--photos", type=Path, required=name in ("check", "apply", "verify", "audit"))
        if name in ("status", "verify", "audit"):
            sub.add_argument("--report", type=Path, required=name != "status")
        if name == "freeze":
            sub.add_argument("--out", type=Path, required=True)
            sub.add_argument("--round", type=int, required=True)
            sub.add_argument("ids", nargs="+")
    add_render_parser(commands)
    sign = commands.add_parser("sign-off")
    sign.add_argument("--report", type=Path, required=True)
    sign.add_argument("--review", type=Path, required=True)
    sign.add_argument("--out", type=Path, required=True)
    return cli


def main():
    cli = parser()
    args = cli.parse_args()
    args.repo = args.repo.resolve()
    if getattr(args, "photos", None):
        args.photos = args.photos.resolve()
    try:
        dispatch(args)
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        cli.exit(1, f"Gallery workflow: {exc}\n")


def dispatch(args):
    if args.command == "freeze":
        freeze(args.repo, args.out, args.ids, args.round)
    elif args.command in ("verify", "audit"):
        verify_site(args)
    elif args.command == "sign-off":
        sign_off(args)
    elif args.command == "render":
        from gallery_prepare import render

        coordinates = args.corners or []
        corners = list(zip(coordinates[::2], coordinates[1::2]))
        render(args.repo, args.round_dir, args.candidate, args.specimen, args.source, corners)
    elif args.command == "apply":
        from gallery_apply import apply_round

        apply_round(args.repo, args.round_dir, args.photos)
    else:
        operation = verify_round if args.command == "check" else read_round
        result = operation(args.repo, args.round_dir, args.photos)
        if args.command == "status":
            current_verification(args, result)
        print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
