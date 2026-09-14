"""Join photographs only through an explicit, validated same-physical-card assertion.

The returned groups are projection inputs; original observations are never rewritten.
Unlinked records retain their existing semantics and representation.
"""

from copy import deepcopy

PHYSICAL_FIELDS = ("finish", "edition", "foilPattern", "markings", "markingRole",
                   "distribution", "cardSize")


def specimen_identity(record):
    return (record.get("setCode"), str(record.get("number", "")).split("/", 1)[0],
            record.get("variant") or "base", record.get("language"))


def observed_fields(observation):
    return [field for field in PHYSICAL_FIELDS
            if observation.get(field) not in (None, "", "unknown", {})]


def photographed_fields(observation):
    return sorted(set(observed_fields(observation)) - set(observation.get("ownerAttestedFields") or []))


def _primary_id(row, by_id):
    sid = row["specimenId"]
    if "sameCardAs" not in row:
        return sid
    link = row["sameCardAs"]
    if not isinstance(link, dict) or set(link) != {"specimenId", "basis"}:
        raise ValueError(f"{sid}: sameCardAs needs specimenId and positive basis")
    if not all(isinstance(link[key], str) and link[key].strip() for key in ("specimenId", "basis")):
        raise ValueError(f"{sid}: sameCardAs needs specimenId and positive basis")
    target = link["specimenId"]
    _validate_target(row, target, by_id)
    return target


def _validate_target(row, target, by_id):
    sid = row["specimenId"]
    if target == sid or target not in by_id:
        raise ValueError(f"{sid}: sameCardAs has a self or missing reference: {target}")
    if "sameCardAs" in by_id[target]:
        raise ValueError(f"{sid}: sameCardAs must point directly to an unlinked primary")
    if specimen_identity(row) != specimen_identity(by_id[target]):
        raise ValueError(f"{sid}: sameCardAs identity differs from {target}")


def _validate_view(row):
    sid = row["specimenId"]
    if not all(row.get(key) for key in ("photograph", "photographSha256", "recordedAt")):
        raise ValueError(f"{sid}: sameCardAs requires a retained, dated photograph with hash")
    obs = row.get("physicalObservation") or {}
    if obs and not str(obs.get("basis") or "").strip():
        raise ValueError(f"{sid}: physicalObservation needs its own basis")
    if obs.get("coversMultipleCards"):
        raise ValueError(f"{sid}: a multi-card frame cannot join a sameCardAs group")
    return obs


def _merge_property(merged, field_sources, sid, field, value):
    if field == "foilPattern":
        value = {"poke ball mirror": "poke-ball", "master ball mirror": "master-ball"}.get(
            " ".join(value.casefold().replace("é", "e").split()), value)
    values = value.items() if field == "distribution" else [(None, value)]
    for key, part in values:
        if part in (None, "", "unknown"):
            continue
        label = f"{field}.{key}" if key is not None else field
        destination = merged.setdefault(field, {}) if key is not None else merged
        slot = key if key is not None else field
        if slot in destination and destination[slot] != part:
            raise ValueError(f"conflicting {label} in sameCardAs views {field_sources[label]} and {sid}")
        destination[slot] = deepcopy(part)
        field_sources.setdefault(label, []).append(sid)


def _group_conflicts(members, specimens):
    member_ids = {row["specimenId"] for row in members}
    conflicts = {ref for row in members
                 for ref in (row.get("physicalObservation") or {}).get("conflictsWith", [])}
    if conflicts & member_ids:
        raise ValueError("sameCardAs group contains an explicit specimen conflict")
    # Incoming conflicts also apply to the whole card, even outside the finish-unit path.
    conflicts.update(row["specimenId"] for row in specimens
                     if member_ids.intersection((row.get("physicalObservation") or {}).get("conflictsWith", [])))
    return sorted(conflicts)


def _combine_group(primary_id, members, specimens):
    members.sort(key=lambda row: (row["specimenId"] != primary_id, row["specimenId"]))
    denominators = {str(row.get("number", "")).split("/", 1)[1].strip()
                    for row in members if "/" in str(row.get("number", ""))} - {""}
    if len(denominators) > 1:
        raise ValueError(f"{primary_id}: sameCardAs has conflicting printed number denominators")
    merged, field_sources = {}, {}
    for row in members:
        obs = _validate_view(row)
        for field in observed_fields(obs):
            _merge_property(merged, field_sources, row["specimenId"], field, obs[field])
    combined = {**deepcopy(members[0]), "_views": members,
                "_fieldSources": {key: sorted(ids) for key, ids in sorted(field_sources.items())}}
    _finish_group_observation(combined, merged, _group_conflicts(members, specimens))
    return combined


def _finish_group_observation(combined, merged, conflicts):
    observed = [row for row in combined["_views"] if row.get("physicalObservation")]
    if observed and not merged.get("finish"):
        raise ValueError(f"{combined['specimenId']}: sameCardAs observations need a positively established finish")
    if merged:
        merged["basis"] = " | ".join(f"{row['specimenId']}: {row['physicalObservation']['basis']}" for row in observed)
        if conflicts:
            merged["conflictsWith"] = conflicts
        combined["physicalObservation"] = merged


def group_specimens(specimens):
    """Return primary records with merged observations and retained ``_views``.

    A sameCardAs link must point directly to an unlinked primary. This deliberately
    rejects chains (including cycles), identity changes and conflicting observations.
    """
    by_id = {row["specimenId"]: row for row in specimens}
    if len(by_id) != len(specimens):
        raise ValueError("duplicate specimen IDs")
    groups = {}
    for sid, row in sorted(by_id.items()):
        target = _primary_id(row, by_id)
        groups.setdefault(target, []).append(row)

    result = []
    for primary_id, members in sorted(groups.items()):
        if len(members) == 1:
            if members[0].get("physicalObservation") and not members[0]["physicalObservation"].get("finish"):
                raise ValueError(f"{primary_id}: an unlinked physical observation needs finish")
            result.append(members[0])
            continue
        result.append(_combine_group(primary_id, members, specimens))
    return result


def projected_specimens(specimens):
    """Index every view against its group's physical facts for graph alignment only."""
    return {view["specimenId"]: {**view, "physicalObservation": group["physicalObservation"],
                                "_group": group} if group.get("_views") else view
            for group in group_specimens(specimens) if group.get("physicalObservation")
            for view in group.get("_views", [group])}
