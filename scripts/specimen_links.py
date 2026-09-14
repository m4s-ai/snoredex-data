"""Resolve retained specimen links through explicit canonical graph references.

These joins expose evidence; they never admit a card, infer a finish, or match nearby numbers.
"""

from collections import defaultdict

from source_registry import provenance_url
from specimen_groups import group_specimens


def specimen_reference_index(specimens, units=()) -> dict[str, set[str]]:
    result = defaultdict(set)
    for group in group_specimens(list(specimens)):
        members = group.get("_views", [group])
        ids = {row["specimenId"] for row in members}
        for specimen in members:
            result[specimen["specimenId"]].update(ids)
            for citation in specimen.get("citedBy") or []:
                result[citation].update(ids)
    for unit in units:
        source_ref = unit.get("sourceRef") or ""
        if source_ref.startswith("specimen:"):
            sid = source_ref.removeprefix("specimen:")
            result[unit["unitId"]].update(result.get(sid, {sid}))
    return result


def physical_specimen_ids(physical) -> set[str]:
    if not physical:
        return set()
    ids = set(physical.get("specimenIds") or [])
    printing_id = physical.get("physicalPrintingId", "")
    if printing_id.startswith("PHYSICAL:specimen:"):
        ids.add(printing_id.removeprefix("PHYSICAL:specimen:"))
    return ids


def release_reference_ids(release, physicals, claims) -> set[str]:
    refs = set(release.get("sourceFirstRecordIds") or [])
    claim_ids = set(release.get("claimIds") or []) | set(release.get("establishingClaimIds") or [])
    for physical in physicals:
        refs.add(physical.get("sourcePrintingId"))
        claim_ids.add(physical.get("establishingClaimId"))
    refs.update(claim_ids)
    for claim_id in claim_ids:
        claim = claims.get(claim_id, {})
        if claim.get("sourceKind") in {
            "legacy-language-unit", "source-first-record", "finish-printing-record"
        }:
            refs.add(claim.get("sourceId"))
    return refs - {None}


def direct_specimen_ids(record, claim) -> set[str]:
    ids = set(record.get("corroboratingSpecimenIds") or []) | set(claim.get("specimenIds") or [])
    if specimen_id := record.get("specimenId"):
        ids.add(specimen_id)
    return ids


def release_specimens(release, physicals, citations, records, claims) -> list[str]:
    linked = set()
    for physical in physicals:
        linked.update(physical_specimen_ids(physical))
    for ref in release_reference_ids(release, physicals, claims):
        linked.update(citations.get(ref, ()))
        linked.update(direct_specimen_ids(records.get(ref, {}), claims.get(ref, {})))
    for sid in list(linked):
        linked.update(citations.get(sid, ()))
    return sorted(linked)


def specimen_provenance_links(ids, specimens) -> set[str]:
    return {value for specimen_id in ids for key in ("listingUrl", "photographSource")
            if (value := provenance_url(specimens.get(specimen_id, {}).get(key)))}


def item_specimen_links(release, physical, citations, records, claims, specimens) -> set[str]:
    ids = release_specimens(release, [physical] if physical else [], citations, records, claims)
    return specimen_provenance_links(ids, specimens)
