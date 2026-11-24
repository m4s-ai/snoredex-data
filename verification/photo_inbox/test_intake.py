"""Checks for the inbox intake script (#656): a job filed without an agent, claiming identity only.

    python verification/photo_inbox/test_intake.py [--photos ../snoredex-photos]

With a photo-archive checkout it also rebuilds SPEC-1125's gallery and preview files byte for byte
from its archived photograph and approved corners.
"""

from io import BytesIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw

from derive import carries_location
import intake
from intake import Refused

sys.path.insert(0, str(intake.ROOT / "scripts"))
import check  # noqa: E402

CORNERS = [[300, 400], [1380, 410], [1370, 1910], [310, 1900]]


def phone_jpeg():
    """A portrait phone photo stored sideways (orientation 6) with GPS, a light card on a dark wall."""
    upright = Image.new("RGB", (1700, 2300), (20, 20, 24))
    ImageDraw.Draw(upright).polygon([tuple(p) for p in CORNERS], fill=(225, 205, 60))
    stored = upright.transpose(Image.Transpose.ROTATE_90)
    exif = Image.Exif()
    exif[274] = 6
    exif.get_ifd(0x8825).update({1: "N", 2: (10.0, 20.0, 30.0), 3: "E", 4: (10.0, 20.0, 30.0)})
    out = BytesIO()
    stored.save(out, "JPEG", exif=exif, quality=92)
    return out.getvalue()


def make_job(folder, item_id, corners=CORNERS, photo=None):
    folder.mkdir(parents=True)
    (folder / "photo.jpg").write_bytes(photo or phone_jpeg())
    job = {"id": "f" * 64, "file": "photo.jpg", "ownPhoto": True, "specimenHint": None, "note": "",
           "receivedAt": "2026-11-25T10:00:00+00:00", "describedAt": "2026-11-25T10:05:00+00:00",
           "itemId": item_id, **({"corners": corners} if corners else {})}
    (folder / "job.json").write_text(json.dumps(job), encoding="utf-8", newline="\n")
    return folder


def items(data):
    """An active verified printing whose image is not an owner photo, and one whose image is."""
    active = [p for p in data["printings"]["printings"] if p["active"] and p["itemKind"] == "verified-printing"]
    plain = next(p for p in active if not intake.owner_image(data, p) and p.get("imageAssetId"))
    owned = next(p for p in active if intake.owner_image(data, p))
    return plain["itemId"], owned["itemId"]


def checked(files):
    """The changed documents pass every check.py rule, read as check.py reads them."""
    model = check.load()
    for name in check.FILES:
        path = f"data/{name}.json"
        if path in files:
            model[name] = json.loads(files[path])
            model["raw"][name] = files[path].encode("utf-8")
    specimens = json.loads(files["verification/specimens.json"])["specimens"]
    model["specimens"] = {row["specimenId"]: row for row in specimens}
    model["photographs"] = {check.PHOTO_DIR + row["photograph"]: row.get("photographSha256")
                            for row in specimens if row.get("photograph")}
    # the image files are checked on disk: place them for the check, then take them away again
    images = [intake.ROOT / name for name, content in files.items() if isinstance(content, bytes)]
    placed = [path for path in images if not path.exists()]
    try:
        for path in placed:
            path.write_bytes(files[path.relative_to(intake.ROOT).as_posix()])
        fired = check.fired(model)
    finally:
        for path in placed:
            path.unlink(missing_ok=True)
    assert not fired, fired


def filing_checks(temp):
    data = intake.model(intake.ROOT)
    plain, owned = items(data)
    job = make_job(temp / "job", plain)
    job_record, corners, data, facts, archive, summary = intake.plan(intake.ROOT, job, temp)
    assert not carries_location(archive), "the archive copy carries no GPS"
    files, kept = intake.changes(data, "SPEC-9999", job_record, corners, facts, summary, archive)
    assert kept is None and {"data/images.json", "data/social.json", "images/previews/SPEC-9999.png"} <= set(files)
    record = json.loads(files["verification/specimens.json"])["specimens"][-1]
    observation = record["physicalObservation"]
    assert observation["ownerAttestedFields"] == ["identity"] and set(observation) == {
        "ownerAttestedFields", "ownerAttestedAt", "basis"}, "identity only: nothing read, nothing copied"
    assert record["recordedAt"] == observation["ownerAttestedAt"] == "2026-11-25", "the assignment's date"
    assert record["photographSha256"] == f"sha256:{summary['sha256']}" and record["citedBy"] == [
        facts["item"]["sourcePrintingId"]]
    claims = json.loads(files["data/claims.json"])
    source = next(r for r in claims["finishPrintings"] if r["printingId"] == facts["item"]["sourcePrintingId"])
    assert source["sources"][0]["providerId"] == "owner-attestation" and source["sources"][0]["source"][
        "sourceRef"] == "specimen:SPEC-9999"
    social = json.loads(files["data/social.json"])
    assert {"itemId": plain, "specimenId": "SPEC-9999", "instagramPosts": [], "postCorners": CORNERS} in social
    gallery = [g for g in json.loads(files["data/images.json"])["galleryImages"] if g["itemId"] == plain]
    assert len(gallery) == 1 and gallery[0]["recipe"] == "intake-spec-9999", "the owner photo replaces the image"
    widths = [image["width"] for image in gallery[0]["images"]]
    assert widths[:2] == [240, 480] and 600 <= widths[2] <= 1200, widths
    checked(files)

    data = intake.model(intake.ROOT)
    owned_job = make_job(temp / "owned", owned)
    job_record, corners, data, facts, archive, summary = intake.plan(intake.ROOT, owned_job, temp)
    files, kept = intake.changes(data, "SPEC-9999", job_record, corners, facts, summary, archive)
    assert kept and "data/images.json" not in files, "an item with an owner photo keeps it"
    checked(files)


def refusal_checks(temp, photos):
    data = intake.model(intake.ROOT)
    plain, _ = items(data)
    cases = {"Druck": make_job(temp / "no-item", None), "Kartenecken sind noch": make_job(temp / "no-corners", plain,
                                                                                       corners=[]),
             "ungültig": make_job(temp / "bad-corners", plain, corners=[[1, 2]] * 3)}
    for reason, folder in cases.items():
        try:
            intake.plan(intake.ROOT, folder, temp)
        except Refused as error:
            assert reason in str(error), (reason, str(error))
        else:
            raise AssertionError(f"not refused: {reason}")
    if photos:
        filed = (photos / intake.PHOTO_DIR / "SPEC-1125.jpg").read_bytes()
        try:
            intake.plan(intake.ROOT, make_job(temp / "again", plain, photo=filed), temp)
        except Refused as error:
            assert "SPEC-1125" in str(error), "the same bytes reuse their SPEC"
        else:
            raise AssertionError("a filed photo was filed again")


def orphan_checks(temp):
    """A copy an interrupted run pushed is found again by its bytes, not filed a second time."""
    data = intake.model(intake.ROOT)
    archive = temp / "archive" / intake.PHOTO_DIR
    archive.mkdir(parents=True)
    (archive / "SPEC-9998.jpg").write_bytes(b"pushed, never recorded")
    (archive / "SPEC-1125.jpg").write_bytes(b"pushed, never recorded")  # named by a record: not an orphan
    digest = intake.sha256(b"pushed, never recorded").hexdigest()
    assert intake.orphan(data, temp / "archive", digest) == "SPEC-9998"
    assert intake.orphan(data, temp / "archive", "0" * 64) is None


def race_checks(temp):
    """Two intakes at once: the one whose push the archive refuses takes the next free number."""
    git = lambda cwd, *args: intake.git(cwd, *args)
    remote, ours, theirs = temp / "remote.git", temp / "ours", temp / "theirs"
    git(temp, "init", "-q", "--bare", "-b", "main", str(remote))
    seed = temp / "seed"
    git(temp, "clone", "-q", str(remote), str(seed))
    (seed / intake.PHOTO_DIR).mkdir(parents=True)
    (seed / intake.PHOTO_DIR / "README").write_text("archive\n", encoding="utf-8", newline="\n")
    for repo in (seed,):
        git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
        git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "seed")
        git(repo, "push", "-q", "origin", "HEAD:main")
    for clone in (ours, theirs):
        git(temp, "clone", "-q", "-b", "main", str(remote), str(clone))
        git(clone, "config", "user.name", "t")
        git(clone, "config", "user.email", "t@t")
    first = intake.free_number(intake.ROOT, ours)
    (theirs / intake.PHOTO_DIR / f"{first}.jpg").write_bytes(b"another intake")
    git(theirs, "add", "-A")
    git(theirs, "commit", "-q", "-m", "another intake")
    git(theirs, "push", "-q")
    data = intake.model(intake.ROOT)
    git_pull = intake.git

    def stale_pull(cwd, *args, check=True):  # ours pulls before the other intake pushes
        if args[:1] == ("pull",) and not hasattr(stale_pull, "done"):
            stale_pull.done = True
            return git_pull(cwd, "status", check=check)
        return git_pull(cwd, *args, check=check)
    intake.git = stale_pull
    try:
        got = intake.reserve(intake.ROOT, ours, b"our photo", intake.sha256(b"our photo").hexdigest(), data)
    finally:
        intake.git = git_pull
    number = int(first.removeprefix("SPEC-"))
    assert got == f"SPEC-{number + 1:04d}", (first, got)
    files = sorted(p.name for p in (ours / intake.PHOTO_DIR).iterdir())
    assert files == ["README", f"{first}.jpg", f"{got}.jpg"] and (ours / intake.PHOTO_DIR / f"{first}.jpg").read_bytes() \
        == b"another intake", "the other intake's photo stays untouched"

    git(ours, "remote", "set-url", "--push", "origin", str(temp / "missing.git"))  # e.g. no write access
    try:
        intake.reserve(intake.ROOT, ours, b"next photo", intake.sha256(b"next photo").hexdigest(), data)
    except Refused as error:
        assert "abgelehnt" in str(error), "a refused push says why, not that another intake was faster"
    else:
        raise AssertionError("a refused push was taken as reserved")
    assert git(ours, "status", "--porcelain").stdout == "" and len(list((ours / intake.PHOTO_DIR).iterdir())) == 3


def reproduction_checks(photos):
    """SPEC-1125's committed gallery and preview files, rebuilt from its archive copy and corners."""
    data = intake.model(intake.ROOT)
    row = next(g for g in data["images"]["galleryImages"] if g["recipe"] == "intake-spec-1125")
    corners = next(r["postCorners"] for r in data["social"] if r["specimenId"] == "SPEC-1125")
    renditions, preview = intake.faces((photos / intake.PHOTO_DIR / "SPEC-1125.jpg").read_bytes(), corners)
    assert [intake.sha256(d).hexdigest() for d in renditions.values()] == [i["sha256"] for i in row["images"]]
    assert preview == (intake.ROOT / "images/previews/SPEC-1125.png").read_bytes()


def main():
    photos = Path(sys.argv[sys.argv.index("--photos") + 1]) if "--photos" in sys.argv else None
    with TemporaryDirectory() as temp:
        temp = Path(temp)
        filing_checks(temp / "filing")
        refusal_checks(temp / "refusals", photos)
        orphan_checks(temp / "orphans")
        (temp / "race").mkdir()
        race_checks(temp / "race")
    if photos:
        reproduction_checks(photos)
    print("intake: all checks passed" + ("" if photos else " (without the photo archive)"))


if __name__ == "__main__":
    main()
