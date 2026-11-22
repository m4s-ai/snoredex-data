"""Select an explicitly attributed photo of one verified physical printing."""
from hashlib import sha256
from pathlib import Path
import re


def photographer_problem(specimen: dict) -> str | None:
    author = specimen.get("photographedBy", "unknown")
    basis = specimen.get("photographedByBasis")
    if author not in ("collection owner", "third party", "unknown"):
        return "invalid photographer"
    if author != "unknown" and (not isinstance(basis, str) or not basis.strip()):
        return "photographer attribution requires evidence"
    if author != "unknown":
        return archive_problem(specimen)
    return None


def archive_problem(specimen: dict) -> str | None:
    name, digest = specimen.get("photograph"), specimen.get("photographSha256")
    expected = re.escape(specimen["specimenId"]) + r"\.(?:jpg|jpeg|png)"
    if not isinstance(name, str) or not re.fullmatch(expected, name, re.IGNORECASE):
        return "photographer attribution requires an archived photograph"
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        return "photographer attribution requires an archive SHA-256"
    return None


def owner_specimen(model: dict, specimen_id: str) -> tuple[dict, dict]:
    """Return the specimen and its one exact active printing, without opening the archive."""
    specimen = model["specimens"].get(specimen_id)
    if not specimen or specimen.get("photographedBy") != "collection owner":
        raise ValueError(f"{specimen_id}: no documented collection-owner photographer")
    if problem := photographer_problem(specimen):
        raise ValueError(f"{specimen_id}: {problem}")
    citation = f"CLAIM:specimen:{specimen_id}"
    cited_printings = set(specimen["citedBy"])
    matches = [item for item in model["printings"]["printings"]
               if item["active"] and item["itemKind"] == "verified-printing"
               and (citation in item["sourceClaimRefs"] or item["sourcePrintingId"] in cited_printings)]
    if len(matches) != 1:
        raise ValueError(f"{specimen_id}: expected one exact verified printing, found {len(matches)}")
    return specimen, matches[0]


def verified_owner_photo(model: dict, specimen_id: str, archive: Path) -> tuple[dict, dict, bytes]:
    """Resolve the exact item and verify the bytes before selecting them for export."""
    specimen, item = owner_specimen(model, specimen_id)
    path = archive / "verification" / "specimens" / specimen["photograph"]
    data = path.read_bytes()
    if "sha256:" + sha256(data).hexdigest() != specimen["photographSha256"]:
        raise ValueError(f"{specimen_id}: archived photograph does not match its SHA-256")
    return specimen, item, data
