"""File one described photo-inbox job as an owner specimen, without an agent and without an AI service (#656).

The owner's assignment of the photo to a printing in the inbox is an owner attestation of that
printing's identity (owner decision, 2026-11-24, #654). The record claims that identity and nothing
read from the face: no finish, edition or marking is copied from the printing or read from the photo.

    python verification/photo_inbox/intake.py I:\\<job> --photos ../snoredex-photos [--pr]

Steps: refuse a job without printing or approved card corners; derive the archive copy (derive.py);
reuse a SPEC whose archived bytes are the same; else take the next free SPEC after the catalogue on
origin/main and the photo archive, and push the copy to the photo archive, which reserves the number
(a copy pushed by an interrupted run is found again by its bytes and reused); then write the specimen,
its citation, preview, gallery images and share row on a new branch, run regen.py --photos (one model
check, with the photo archive), and commit. `--pr` pushes the branch and opens the pull request; `--dry-run` writes
nothing and prints what it would file. The branch is printed; `--result FILE` also writes what was
filed as JSON (`outcome`), which the inbox's intake run reads (#675).
"""

from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "verification")]
from card_pages import checked_corners  # noqa: E402
from check import dump  # noqa: E402
from derive import derive  # noqa: E402
from gallery_prepare import extract, resize  # noqa: E402

PHOTO_DIR = "verification/specimens"
ASSET_NAMESPACE = "https://github.com/m4s-ai/snoredex-data/asset/v1/"
SPEC = re.compile(r"SPEC-([0-9]{4,8})")
OWNER_BASIS = ("Owner decision of 2026-11-23: every photograph in the private photo inbox is the collection "
               "owner's own.")


class Refused(Exception):
    """The job cannot be filed as it is; the message says why, in the inbox's language."""


def git(cwd, *args, check=True):
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if check and done.returncode:
        raise Refused(f"git {' '.join(args)}: {done.stderr.strip()}")
    return done


def today():
    return datetime.now(timezone.utc).date().isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def job_input(folder, corners=None):
    """The job's printing and approved corners; a job missing either is not ready."""
    job = read_json(Path(folder) / "job.json")
    if not job.get("itemId"):
        raise Refused("Dem Foto ist noch kein Druck zugeordnet.")
    corners = corners or job.get("corners")
    if not corners:
        raise Refused("Die Kartenecken sind noch nicht freigegeben.")
    try:
        corners = [[int(x), int(y)] for x, y in corners]
        checked_corners(corners, job["itemId"])
    except (TypeError, ValueError) as error:
        raise Refused("Die freigegebenen Kartenecken sind ungültig.") from error
    number_guard(job)
    return job, corners


def number_guard(job):
    """A collector number read from the face that contradicts the printing stops intake until the owner
    confirms the assignment (#658); an unreadable or unchecked number stops nothing."""
    check = job.get("numberCheck") or {}
    if check.get("itemId") == job["itemId"] and check.get("result") == "mismatch" and not job.get("numberConfirmedAt"):
        read = ", ".join(check.get("read") or [])
        raise Refused(f"Gelesen wurde {read}, der Druck hat {check.get('expected')}. "
                      "Bitte die Zuordnung prüfen oder im Eingang bestätigen.")


def model(root):
    data = {name: read_json(root / f"data/{name}.json") for name in ("printings", "claims", "images", "sets")}
    data["specimens"] = read_json(root / "verification/specimens.json")
    data["social"] = read_json(root / "data/social.json")
    return data


def printing_facts(data, item_id):
    """What identifies the assigned printing: the labels a specimen record carries."""
    item = next((p for p in data["printings"]["printings"] if p["itemId"] == item_id and p["active"]), None)
    if item is None or item["itemKind"] != "verified-printing":
        raise Refused("Der zugeordnete Druck ist kein aktiver, geprüfter Druck des Katalogs.")
    sets = data["sets"]
    edition = next(e for e in sets["setEditions"] if e["setEditionId"] == item["setEditionId"])
    local_set = next(s for s in sets["localSets"] if s["localSetId"] == edition["localSetId"])
    language = next(loc["displayName"] for loc in sets["localizations"]
                    if loc["localizationId"] == edition["localizationId"])
    printed = next((c["printedSetCode"] for c in sets["setEditionCodes"]
                    if c["setEditionId"] == item["setEditionId"] and c.get("printedSetCode")), None)
    number = "/".join(filter(None, (item["collectorNumber"], item.get("collectorNumberDenominator"))))
    return {"item": item, "setCode": printed or local_set["localSetCode"], "number": number,
            "language": language, "setName": local_set["localSetName"], "variant": variant(data, item),
            "cites": cited_as(data, item)}


def cited_as(data, item):
    """How a specimen names this printing: a legacy printing by its finish-store row, a source-first
    printing by its source-first key. Resolved before anything is written or pushed."""
    if item.get("sourcePrintingId"):
        if not any(r["printingId"] == item["sourcePrintingId"] for r in data["claims"]["finishPrintings"]):
            raise Refused(f"Zum Druck fehlt die Zeile {item['sourcePrintingId']} im Katalog.")
        return item["sourcePrintingId"]
    keys = [ref.removeprefix("CLAIM:source-first:") for ref in item["sourceClaimRefs"]
            if ref.startswith("CLAIM:source-first:")]
    if len(keys) != 1:
        raise Refused("Der Druck lässt sich keiner Katalogquelle eindeutig zuordnen.")
    return keys[0]


def variant(data, item):
    """The legacy product's variant token (V1, V2 ...), else base: an identity label, not a finish."""
    row = next((r for r in data["claims"]["finishPrintings"] if r["printingId"] == item["sourcePrintingId"]), {})
    product = next((p for p in data["claims"]["legacyProducts"] if p["productId"] == row.get("productId")), {})
    return product.get("variantToken") or "base"


def registered(data):
    return {row["photographSha256"]: row["specimenId"] for row in data["specimens"]["specimens"]
            if row.get("photographSha256")}


def free_number(root, photos):
    """The next SPEC after every id on origin/main and every file in the photo archive."""
    git(root, "fetch", "-q", "origin")
    main = json.loads(git(root, "show", "origin/main:verification/specimens.json").stdout)
    ids = [int(SPEC.fullmatch(row["specimenId"])[1]) for row in main["specimens"]]
    ids += [int(m[1]) for path in (photos / PHOTO_DIR).glob("SPEC-*.*") if (m := SPEC.match(path.stem))]
    return f"SPEC-{max(ids) + 1:04d}"


def orphan(data, photos, digest):
    """A copy an interrupted run pushed but never recorded: found again by its bytes."""
    named = {row.get("photograph") for row in data["specimens"]["specimens"]}
    for path in sorted((photos / PHOTO_DIR).glob("SPEC-*.jpg")):
        if path.name not in named and sha256(path.read_bytes()).hexdigest() == digest:
            return path.stem
    return None


def reserve(root, photos, archive, digest, data):
    """Push the archive copy, which reserves its number; a lost race takes the next one."""
    # a retry resets this run's own commit: nothing else in the checkout may be at stake
    if git(photos, "status", "--porcelain").stdout.strip():
        raise Refused("Der Checkout des Fotoarchivs hat ungesicherte Änderungen.")
    git(photos, "pull", "-q", "--ff-only")
    found = orphan(data, photos, digest)
    if found:
        return found
    for _ in range(3):
        specimen = free_number(root, photos)
        path = photos / PHOTO_DIR / f"{specimen}.jpg"
        with path.open("xb") as file:
            file.write(archive)
        git(photos, "add", f"{PHOTO_DIR}/{path.name}")
        git(photos, "commit", "-q", "-m", f"Add {specimen}: owner photograph from the private photo inbox (#656)")
        pushed = git(photos, "push", "-q", check=False)
        if pushed.returncode == 0:
            return specimen
        git(photos, "reset", "-q", "--hard", "HEAD~1")  # only this run's own commit, not yet pushed
        git(photos, "pull", "-q", "--ff-only")
        if not path.exists():  # nobody took the number: the push failed for another reason
            raise Refused(f"Der Push ins Fotoarchiv wurde abgelehnt: {pushed.stderr.strip()}")
    raise Refused("Das Fotoarchiv hat dreimal eine andere Übernahme zuerst angenommen. Bitte erneut starten.")


def faces(archive, corners):
    """Gallery renditions and preview, exactly as the specimen-intake skill and gallery_prepare make them."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(archive)) as image:
        upright = ImageOps.exif_transpose(image)
        icc = image.info.get("icc_profile")
        rgba = upright.convert("RGBA")
        rgb = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
    try:
        face, _ = extract(rgb, [tuple(pair) for pair in corners])
    except ValueError as error:
        raise Refused(f"Die Karte ist zu klein oder die Ecken passen nicht: {error}") from error
    files = {}
    for width in (240, 480, min(1200, face.width)):
        buffer = io.BytesIO()
        resize(face, width).save(buffer, "WEBP", quality=90, method=6)
        files[width] = buffer.getvalue()
    thumb = resize(face, 360).quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    buffer = io.BytesIO()
    thumb.save(buffer, "PNG", optimize=True, icc_profile=icc)
    return files, buffer.getvalue()


def specimen_record(specimen, job, facts, summary):
    attested = (job.get("describedAt") or job["receivedAt"])[:10]
    item = facts["item"]
    kind = "DNG, whose embedded full-size preview JPEG was extracted byte for byte" if summary["file"].endswith(
        ".dng") else "JPEG, whose image data was filed unchanged"
    note = f'; the owner noted "{job["note"]}"' if job.get("note") else ""
    return {
        "specimenId": specimen, "photographedBy": "collection owner",
        "photographedByBasis": f"{OWNER_BASIS} Uploaded through the private photo inbox on "
                               f"{job['receivedAt'][:10]}, job {job['id']}{note}.",
        "setCode": facts["setCode"], "number": facts["number"], "variant": facts["variant"],
        "language": facts["language"], "heldBy": "collection owner",
        "inspectedFrom": f"Owner photograph uploaded through the private photo inbox as a {kind}; metadata reduced "
                         "to the orientation tag and the ICC colour profile (Exif including GPS, XMP and maker data "
                         "removed); the filed image decodes pixel-identical to its source. Filed by the inbox intake "
                         f"script (#656): {summary['width']}x{summary['height']} stored, Exif orientation "
                         f"{summary['orientation'] or 1}.",
        "photograph": f"{specimen}.jpg", "photographSource": None, "photographSha256": f"sha256:{summary['sha256']}",
        "observed": "Not read from the face: filed by the inbox intake script. The photograph's identity rests on "
                    f"the owner's assignment to printing {facts['cites']} ({facts['language']} "
                    f"{facts['setCode']} {facts['number']}); no finish, edition or marking is recorded from it.",
        "recordedAt": attested, "citedBy": [facts["cites"]],
        "physicalObservation": {
            "ownerAttestedFields": ["identity"], "ownerAttestedAt": attested,
            "basis": f"The owner assigned this photograph to {item['itemId']} (printing {facts['cites']}) "
                     f"in the private photo inbox on {attested}."},
        "listingUrl": None,
    }


def citation(specimen, facts, attested):
    return {"providerId": "owner-attestation", "source": {
        "claimFields": ["identity"],
        "evidence": f"The owner assigned the photograph {specimen} to this printing ({facts['language']} "
                    f"{facts['setCode']} {facts['number']}) in the private photo inbox. Identity only; no finish, "
                    "edition or marking is asserted from the photograph.",
        "retrievedAt": attested, "sourceRef": f"specimen:{specimen}",
        "sourceType": "Owner assignment in the private photo inbox"}}


def gallery_row(item_id, specimen, path, renditions):
    images = []
    for data in renditions.values():
        from PIL import Image

        with Image.open(io.BytesIO(data)) as image:
            digest = sha256(data).hexdigest()
            images.append({"width": image.width, "height": image.height,
                           "path": f"images/gallery/{digest}.webp", "sha256": digest})
    return {"itemId": item_id, "recipe": f"intake-{specimen.lower()}", "mediaKind": "photo",
            "scope": "exact-printing", "source": path, "images": images}


def owner_image(data, item):
    """The specimen an item's image already is, when the collection owner photographed it."""
    asset = next((a for a in data["images"]["assets"] if a["assetId"] == item.get("imageAssetId")), {})
    owners = {f"{PHOTO_DIR}/{row['photograph']}": row["specimenId"] for row in data["specimens"]["specimens"]
              if row.get("photographedBy") == "collection owner" and row.get("photograph")}
    return owners.get(asset.get("path"))


def changes(data, specimen, job, corners, facts, summary, archive):
    """Every file the filing writes, by repository path; an item with an owner photo keeps it."""
    item, attested = facts["item"], (job.get("describedAt") or job["receivedAt"])[:10]
    data["specimens"]["specimens"].append(specimen_record(specimen, job, facts, summary))
    data["specimens"]["count"] = len(data["specimens"]["specimens"])
    out = {"verification/specimens.json": json.dumps(data["specimens"], ensure_ascii=False, indent=2) + "\n"}
    if item.get("sourcePrintingId"):  # a legacy printing: its finish-store row cites the specimen
        row = next(r for r in data["claims"]["finishPrintings"] if r["printingId"] == item["sourcePrintingId"])
        row["sources"].insert(0, citation(specimen, facts, attested))
        out["data/claims.json"] = dump(data["claims"])
    else:  # a source-first printing names its specimens among its own claim references
        item["sourceClaimRefs"].append(f"CLAIM:specimen:{specimen}")
        out["data/printings.json"] = dump(data["printings"])
    kept = owner_image(data, item)
    if not kept:
        out.update(imaging(data, specimen, item, facts, corners, archive))
    return out, kept


def imaging(data, specimen, item, facts, corners, archive):
    path = f"{PHOTO_DIR}/{specimen}.jpg"
    renditions, preview = faces(archive, corners)
    asset_id = f"asset-{uuid.uuid5(uuid.NAMESPACE_URL, ASSET_NAMESPACE + path)}"
    images = data["images"]
    images["assets"] = sorted(images["assets"] + [{
        "assetId": asset_id, "path": path, "sha256": f"sha256:{sha256(archive).hexdigest()}",
        "imageScope": "exact-printing", "altTextBasis": f"{item['cardName']} — {facts['setName']}; exact-printing",
        "preview": f"images/previews/{specimen}.png"}], key=lambda a: a["assetId"])
    images["galleryImages"] = sorted([g for g in images["galleryImages"] if g["itemId"] != item["itemId"]] +
                                     [gallery_row(item["itemId"], specimen, path, renditions)],
                                     key=lambda g: g["itemId"])
    item["imageAssetId"] = asset_id
    data["printings"]["meta"].update(dataAsOf=today(), siteGenerated=today())
    if not any(r["itemId"] == item["itemId"] for r in data["social"]):
        data["social"].append({"itemId": item["itemId"], "specimenId": specimen, "instagramPosts": [],
                               "postCorners": corners})
    files = {f"images/gallery/{sha256(d).hexdigest()}.webp": d for d in renditions.values()}
    files[f"images/previews/{specimen}.png"] = preview
    return {"data/images.json": dump(images), "data/printings.json": dump(data["printings"]),
            "data/social.json": json.dumps(data["social"], ensure_ascii=False, indent=2) + "\n", **files}


def write_files(root, files):
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")


def gate(root, photos, run=subprocess.run):
    """regen.py once (#677): it builds the outputs and checks the model a single time, with the photo
    archive's originals and their SHA-256 (check.py --photos as its first step)."""
    done = run([sys.executable, "scripts/regen.py", "--photos", str(photos)], cwd=root, capture_output=True, text=True)
    if done.returncode:
        lines = [line for line in (done.stdout + done.stderr).strip().splitlines() if not line.startswith("===")]
        failed = next((line for line in reversed(lines) if line.startswith("regen.py: FAILED at ")), "")
        reason = next((line for line in reversed(lines) if not line.startswith("regen.py:")), done.returncode)
        raise Refused(f"{failed.removeprefix('regen.py: FAILED at ') or 'regen.py'} schlägt fehl: {reason}")


def deliver(root, specimen, facts, kept, open_pr):
    branch = f"intake/{specimen}"
    git(root, "add", "-A")
    message = (f"File {specimen}: owner photograph of {facts['language']} {facts['setCode']} {facts['number']} "
               f"(#656)\n\nFiled by the inbox intake script from the owner's assignment to "
               f"{facts['item']['sourcePrintingId']}; identity only."
               + (f" The item keeps its owner photograph {kept}." if kept else ""))
    git(root, "commit", "-q", "-m", message)
    if open_pr:
        git(root, "push", "-q", "-u", "origin", branch)
        subprocess.run(["gh", "pr", "create", "--base", "main", "--head", branch, "--title",
                        f"File {specimen} from the photo inbox (#656)", "--body",
                        f"{message.splitlines()[0]}\n\nOpened by `verification/photo_inbox/intake.py`."],
                       cwd=root, check=True)
    return branch


def outcome(branch, specimen, item_id, kept):
    """What a filing hands its caller: `keeps` names the owner photo the printing keeps as its image, so
    the new SPEC is a further piece of evidence only (owner decision D03, #675), else it is None."""
    return {"branch": branch, "specimen": specimen, "itemId": item_id, "keeps": kept}


def plan(root, folder, photos, corners=None):
    """Everything up to the archive copy; refuses before anything is written."""
    job, corners = job_input(folder, corners)
    data = model(root)
    facts = printing_facts(data, job["itemId"])
    archive, summary = derive(Path(folder))
    known = registered(data).get(f"sha256:{summary['sha256']}")
    if known:
        raise Refused(f"Das Foto ist schon als {known} übernommen.")
    return job, corners, data, facts, archive, summary


def main(argv=None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path, help="the job folder in the inbox's data folder or its share")
    parser.add_argument("--photos", type=Path, required=True, help="checkout of m4s-ai/snoredex-photos")
    parser.add_argument("--corners", type=int, nargs=8, metavar="PX", help="instead of the job's approved corners")
    parser.add_argument("--pr", action="store_true", help="push the branch and open the pull request")
    parser.add_argument("--dry-run", action="store_true", help="write nothing, print what would be filed")
    parser.add_argument("--result", type=Path, help="also write what was filed to this JSON file")
    args = parser.parse_args(argv)
    corners = [args.corners[i:i + 2] for i in range(0, 8, 2)] if args.corners else None
    try:
        job, corners, data, facts, archive, summary = plan(ROOT, args.job, args.photos, corners)
        if args.dry_run:
            files, kept = changes(data, "SPEC-DRYRUN", job, corners, facts, summary, archive)
            print(json.dumps({"item": job["itemId"], "archiveSha256": summary["sha256"], "keeps": kept,
                              "files": sorted(files)}, indent=1))
            return 0
        if git(ROOT, "status", "--porcelain").stdout.strip():
            raise Refused("Der Checkout hat ungesicherte Änderungen.")
        specimen = reserve(ROOT, args.photos, archive, summary["sha256"], data)
        git(ROOT, "switch", "-q", "-c", f"intake/{specimen}", "origin/main")
        data = model(ROOT)
        facts = printing_facts(data, job["itemId"])
        files, kept = changes(data, specimen, job, corners, facts, summary, archive)
        write_files(ROOT, files)
        gate(ROOT, args.photos)
        branch = deliver(ROOT, specimen, facts, kept, args.pr)
        if args.result:
            args.result.write_text(json.dumps(outcome(branch, specimen, job["itemId"], kept)) + "\n",
                                   encoding="utf-8", newline="\n")
        print(branch)
    except Refused as error:
        print(f"Übernahme zurückgestellt: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
