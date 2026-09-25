#!/usr/bin/env python3
"""Run bounded workflow loops for evidence, physical proof, discovery, News/Promo, TCGdex,
absence, and Cardmarket boundaries.

This is orchestration, not a second truth writer. Each cycle delegates to the scoped-lane runner
or, for an explicit live discovery request, to the existing retained-run refresh wrapper. The
state evaluator reports when owner input or a new positive source is required and stops instead of
spinning on an unchanged metric.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
MANIFEST = ROOT / "verification" / "workflow_loop_manifest.json"
EVIDENCE = ROOT / "verification" / "evidence_semantics.json"
SOURCE_ADAPTERS = ROOT / "verification" / "source_adapters.json"
SOURCE_STAGING = ROOT / "verification" / "source_adapter_staging.json"
SOURCE_RECORDS = ROOT / "verification" / "source_adapter_records.jsonl"
CARD_ADAPTERS = ROOT / "verification" / "card_discovery_adapters.json"
CARD_STAGING = ROOT / "verification" / "card_discovery_staging.json"
CARD_RECORDS = ROOT / "verification" / "card_discovery_records.jsonl"
SOURCE_RUNS = ROOT / "verification" / "runs" / "source-adapters"
CARD_RUNS = ROOT / "verification" / "runs" / "card-discovery"
SNAPSHOT = ROOT / "verification" / "finish_tcgdex_snapshot.json"
CANDIDATE = ROOT / "verification" / "cache" / "finish-tcgdex" / "refresh-candidate.json"
ADJUDICATIONS = ROOT / "verification" / "owner_adjudications.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SET_SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
CARDMARKET_BASELINE = ROOT / "legacy-cardmarket-baseline.json"
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


class WorkflowLoopError(ValueError):
    """A retained run cannot be identified safely from its manifest."""


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_staging(path: pathlib.Path) -> dict[str, Any]:
    """Missing or malformed staging is stale work, not a state-evaluation failure."""
    try:
        document = read_json(path)
    except (OSError, TypeError, ValueError):
        return {}
    return document if isinstance(document, dict) else {}


def latest_manifests(directory: pathlib.Path) -> list[dict[str, Any]]:
    paths = []
    for path in directory.glob("*/manifest.json"):
        manifest = read_json(path)
        run_id = manifest.get("runId")
        if run_id != path.parent.name:
            raise WorkflowLoopError(
                f"run directory and manifest id differ: {path.parent.name}"
            )
        paths.append((run_id, manifest))
    if not paths:
        return []
    # Run IDs are the fachliche acquisition order (YYYYMMDDTHHMMSSZ), unlike mtime which can be
    # changed by checkout, copying, or an interrupted retry.
    return [max(paths, key=lambda item: item[0])[1]]


def canonical_manifest(directory: pathlib.Path, kind: str) -> dict[str, Any] | None:
    """Read the newest complete run selected by the owning adapter's compatibility contract."""
    if kind == "source":
        try:
            from scripts import source_adapters as adapter
        except ImportError:  # direct execution from scripts/
            import source_adapters as adapter  # type: ignore[no-redef]
        contract, capability = adapter.load_inputs()
        run_id = adapter.newest_compatible_complete_run(contract, capability)
    elif kind == "card":
        try:
            from scripts import card_discovery as adapter
        except ImportError:  # direct execution from scripts/
            import card_discovery as adapter  # type: ignore[no-redef]
        contract, capability, _identity = adapter.load_inputs()
        run_id = adapter.newest_compatible_complete_run(contract, capability)
    else:
        raise ValueError(f"unknown discovery run kind: {kind}")
    if not run_id:
        return None
    path = directory / run_id / "manifest.json"
    manifest = read_json(path)
    if manifest.get("runId") != run_id:
        raise WorkflowLoopError(f"canonical run manifest id differs: {run_id}")
    return manifest


def _staging_matches_inputs(
    staging_meta: dict[str, Any], card_canonical: dict[str, Any] | None,
    contract_hash: str, capability_graph_hash: str, authoritative_graph_hash: str,
) -> bool:
    """A run id alone does not make staging current after reconciliation inputs change."""
    return bool(
        card_canonical
        and staging_meta.get("generatedFromRun") == card_canonical.get("runId")
        and staging_meta.get("contractHash") == contract_hash
        and staging_meta.get("capabilityGraphHash") == capability_graph_hash
        and staging_meta.get("authoritativeGraphHash") == authoritative_graph_hash
    )


def _records_projection_matches(
    staging: dict[str, Any], records_path: pathlib.Path,
) -> bool:
    """A staging summary is stale if its generated records projection is not intact."""
    expected_hash = staging.get("recordsHash")
    if not isinstance(expected_hash, str):
        return False
    try:
        actual_hash = "sha256:" + hashlib.sha256(records_path.read_bytes()).hexdigest()
    except OSError:
        return False
    return actual_hash == expected_hash


def _source_staging_matches_inputs(
    staging: dict[str, Any], records_path: pathlib.Path,
    source_canonical: dict[str, Any] | None,
    contract_hash: str, capability_graph_hash: str,
) -> bool:
    """Source staging is current only for its canonical run, inputs, and records bytes."""
    meta = staging.get("meta", {})
    if not isinstance(meta, dict):
        return False
    return bool(
        source_canonical
        and meta.get("generatedFromRun") == source_canonical.get("runId")
        and meta.get("contractHash") == contract_hash
        and meta.get("capabilityGraphHash") == capability_graph_hash
        and _records_projection_matches(staging, records_path)
    )


def _source_replay_state(
    source_canonical: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    try:
        from scripts import source_adapters as adapter
    except ImportError:  # direct execution from scripts/
        import source_adapters as adapter  # type: ignore[no-redef]
    contract, capability = adapter.load_inputs()
    current = _source_staging_matches_inputs(
        _read_staging(SOURCE_STAGING), SOURCE_RECORDS, source_canonical,
        adapter.content_hash(contract),
        adapter.capability_pin(capability, adapter.manifest_surfaces(source_canonical or {})),
    )
    if current:
        return True, None
    return False, adapter.newest_acquisition_compatible_complete_run(contract)


def _card_replay_source(
    adapter: Any, contract: dict[str, Any], staging_is_current: bool,
) -> str | None:
    return None if staging_is_current else adapter.newest_acquisition_compatible_complete_run(
        contract
    )


def _completeness_matches_inputs(inputs: dict[str, Any], errors: list[str],
                                 current_text: str, summary: dict[str, Any]) -> bool:
    """Compare the retained completeness projection with its complete current inputs."""
    if errors:
        return False
    expected = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    return current_text == expected


def _completeness_is_current() -> bool:
    try:
        from scripts import completeness_gate
    except ImportError:  # direct execution from scripts/
        import completeness_gate  # type: ignore[no-redef]
    try:
        inputs, errors = completeness_gate.validate_inputs()
        current_text = completeness_gate.OUTPUT.read_text(encoding="utf-8")
        return _completeness_matches_inputs(
            inputs, errors, current_text, completeness_gate.summary(inputs),
        )
    except (OSError, KeyError, TypeError, ValueError):
        # Treat malformed/missing inputs as pending projection work. The owning gate command
        # reports the concrete validation error; the loop must not mistake the old output as current.
        return False


def evidence_state() -> dict[str, Any]:
    counts = read_json(EVIDENCE)["counts"]["applicationStatuses"]
    if counts.get("needs-evidence", 0):
        state = "needs-evidence"
    elif counts.get("disputed", 0):
        state = "needs-adjudication"
    else:
        state = "terminal"
    return {"state": state, "progress": {key: counts.get(key, 0) for key in sorted(counts)}}


def physical_state() -> dict[str, Any]:
    specimens = read_json(SPECIMENS)["specimens"]
    active_specimens = [specimen for specimen in specimens if specimen.get("physicalObservation")]
    observations = len(active_specimens)
    photographs = sum(bool(specimen.get("photographSha256")) for specimen in specimens)
    attachments = sum(bool(specimen.get("photograph")) for specimen in specimens)
    if not specimens:
        state = "issue"
    elif active_specimens:
        # A positive observation is the active input for this lane. Historical specimen rows may
        # intentionally have no observation; their absence must not block a newly observed card.
        state = "observed"
    else:
        state = "specimen"
    return {
        "state": state,
        "progress": {
            "specimenCount": len(specimens),
            "activeSpecimenCount": len(active_specimens),
            "historicalUnobservedCount": len(specimens) - len(active_specimens),
            "physicalObservationCount": observations,
            "photographHashCount": photographs,
            "attachmentCount": attachments,
        },
    }


def _discovery_outcome(blocked: int, needs_source: int, new_candidates: int) -> str:
    if new_candidates:
        return "needs-reconciliation"
    if blocked:
        return "blocked-by-source"
    if needs_source:
        return "needs-source"
    return "terminal"


def _stale_projection_needs_source(
    source_records_current: bool, staging_is_current: bool,
    source_replay_available: bool, card_replay_available: bool,
) -> bool:
    return (
        (not source_records_current and not source_replay_available)
        or (not staging_is_current and not card_replay_available)
    )


def _stale_projection_state(
    source_records_current: bool, staging_is_current: bool,
    source_replay_available: bool, card_replay_available: bool,
) -> str:
    return "needs-source" if _stale_projection_needs_source(
        source_records_current, staging_is_current,
        source_replay_available, card_replay_available,
    ) else "retained"


def _discovery_state(
    source: list[dict[str, Any]], cards: list[dict[str, Any]],
    source_canonical: dict[str, Any] | None, card_canonical: dict[str, Any] | None,
    blocked: int, needs_source: int, new_candidates: int, staging_is_current: bool,
    completeness_is_current: bool, source_records_current: bool = True,
    source_replay_available: bool = True, card_replay_available: bool = True,
) -> str:
    if not source or not cards:
        return "candidate"
    if not staging_is_current or not source_records_current:
        return _stale_projection_state(
            source_records_current, staging_is_current,
            source_replay_available, card_replay_available,
        )
    if not source_canonical or not card_canonical:
        return "retained"
    # Newer failed or incomplete attempts are diagnostic only. The selected compatible
    # complete manifests remain the canonical basis for staging and reconciliation.
    if (source_canonical.get("status") != "complete"
            or card_canonical.get("status") != "complete"):
        return "retained"
    if not completeness_is_current:
        return "retained"
    return _discovery_outcome(blocked, needs_source, new_candidates)


def _discovery_progress(
    source: list[dict[str, Any]], cards: list[dict[str, Any]],
    source_canonical: dict[str, Any] | None, card_canonical: dict[str, Any] | None,
    failures: int, blocked: int, needs_source: int, total_gaps: int,
    new_candidates: int, staged_candidates: int, staging_run: str | None,
    staging_is_current: bool, source_records_current: bool,
    source_replay_run: str | None, card_replay_run: str | None,
    completeness_is_current: bool,
) -> dict[str, Any]:
    latest_source = next(iter(source), {})
    latest_cards = next(iter(cards), {})
    selected_source = source_canonical or {}
    selected_cards = card_canonical or {}
    return {
        "sourceRun": selected_source.get("runId"),
        "cardRun": selected_cards.get("runId"),
        "sourceLatestAttempt": latest_source.get("runId"),
        "cardLatestAttempt": latest_cards.get("runId"),
        "sourceStatus": latest_source.get("status"),
        "cardStatus": latest_cards.get("status"),
        "sourceCanonicalStatus": selected_source.get("status"),
        "cardCanonicalStatus": selected_cards.get("status"),
        "failures": failures,
        "blockedGaps": blocked,
        "needsSourceGaps": needs_source,
        "totalGaps": total_gaps,
        "newCandidateRecords": new_candidates,
        "stagingCandidateRecords": staged_candidates,
        "stagingRun": staging_run,
        "stagingMatchesCanonicalInputs": staging_is_current,
        "sourceRecordsCurrent": source_records_current,
        "sourceReplayRun": source_replay_run,
        "cardReplayRun": card_replay_run,
        "completenessMatchesInputs": completeness_is_current,
    }


def discovery_state() -> dict[str, Any]:
    source = latest_manifests(SOURCE_RUNS)
    cards = latest_manifests(CARD_RUNS)
    source_canonical = canonical_manifest(SOURCE_RUNS, "source")
    card_canonical = canonical_manifest(CARD_RUNS, "card")
    gaps = read_json(SOURCE_ADAPTERS)["gaps"] + read_json(CARD_ADAPTERS)["gaps"]
    failures = sum(len(manifest.get("failures", [])) for manifest in source + cards)
    blocked = sum(gap.get("terminalState") == "blocked-by-source" for gap in gaps)
    needs_source = sum(gap.get("terminalState") == "needs-evidence" for gap in gaps)
    try:
        from scripts import card_discovery as adapter
    except ImportError:  # direct execution from scripts/
        import card_discovery as adapter  # type: ignore[no-redef]
    contract, capability, identity = adapter.load_inputs()
    source_records_current, source_replay_run = _source_replay_state(source_canonical)
    staging_document = _read_staging(CARD_STAGING)
    staging_meta = staging_document.get("meta", {})
    if not isinstance(staging_meta, dict):
        staging_meta = {}
    staging_run = staging_meta.get("generatedFromRun")
    staging_is_current = _staging_matches_inputs(
        staging_meta, card_canonical,
        adapter.content_hash(contract),
        adapter.capability_pin(capability, adapter.manifest_surfaces(card_canonical or {})),
        identity.get("authoritativeGraphHash", adapter.content_hash(identity)),
    ) and _records_projection_matches(staging_document, CARD_RECORDS)
    card_replay_run = _card_replay_source(adapter, contract, staging_is_current)
    counts = staging_meta.get("counts", {})
    staged_candidates = counts.get("newCandidate", 0) if isinstance(counts, dict) else 0
    new_candidates = staged_candidates if staging_is_current else 0
    completeness_is_current = _completeness_is_current()
    return {
        "state": _discovery_state(
            source, cards, source_canonical, card_canonical, blocked, needs_source,
            new_candidates, staging_is_current, completeness_is_current,
            source_records_current,
            source_replay_available=source_replay_run is not None,
            card_replay_available=card_replay_run is not None,
        ),
        "progress": _discovery_progress(
            source, cards, source_canonical, card_canonical,
            failures, blocked, needs_source, len(gaps), new_candidates,
            staged_candidates, staging_run, staging_is_current,
            source_records_current, source_replay_run, card_replay_run,
            completeness_is_current,
        ),
    }


def tcgdex_state() -> dict[str, Any]:
    snapshot_records = len(read_json(SNAPSHOT)["records"])
    candidate_records = None
    candidate_hash = None
    if CANDIDATE.is_file():
        candidate = read_json(CANDIDATE)
        candidate_records = len(candidate.get("records", candidate))
        candidate_hash = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
    if candidate_records is None:
        state = "needs-refresh"
    else:
        state = "needs-acceptance"
    return {
        "state": state,
        "progress": {
            "snapshotRecords": snapshot_records,
            "candidateRecords": candidate_records,
            "candidateHash": candidate_hash,
        },
    }


def news_promo_state() -> dict[str, Any]:
    records = read_json(SET_SOURCES)["sourceRecords"]
    newsish = []
    leads = []
    claims = []
    for record in records:
        text = json.dumps(record, ensure_ascii=False).lower()
        kind = str(record.get("sourceKind", "")).lower()
        if any(token in text for token in ("news", "announcement", "promo")):
            newsish.append(record)
        if kind in {"news-lead", "promo-lead", "announcement-lead"}:
            leads.append(record)
        raw = record.get("raw") or {}
        if kind in {"news-lead", "promo-lead", "announcement-lead"} and (raw.get("snorlaxPrintIds") or raw.get("cardIds")):
            claims.append(record)
    if not leads:
        state = "needs-source"
    elif leads and not newsish:
        state = "lead"
    elif leads and not claims:
        state = "concrete-source"
    elif claims:
        state = "graph"
    elif newsish:
        state = "needs-source"
    else:
        state = "needs-source"
    return {
        "state": state,
        "progress": {
            "sourceRecordCount": len(records),
            "newsPromoRecordCount": len(newsish),
            "leadCount": len(leads),
            "positiveClaimCount": len(claims),
        },
    }


def absence_state() -> dict[str, Any]:
    counts = read_json(EVIDENCE)["counts"]["applicationStatuses"]
    decisions = read_json(ADJUDICATIONS)["decisions"]
    if counts.get("disputed", 0):
        state = "needs-adjudication"
    elif counts.get("not-printed", 0) and not counts.get("needs-evidence", 0):
        state = "terminal"
    else:
        state = "scope"
    return {
        "state": state,
        "progress": {
            "disputed": counts.get("disputed", 0),
            "notPrinted": counts.get("not-printed", 0),
            "needsEvidence": counts.get("needs-evidence", 0),
            "ownerDecisions": len(decisions),
        },
    }


def cardmarket_state() -> dict[str, Any]:
    specimens = read_json(SPECIMENS)["specimens"]
    baseline = read_json(CARDMARKET_BASELINE)
    cards = baseline.get("members", {}).get("cards", [])
    listings = [specimen for specimen in specimens if specimen.get("listingUrl")]
    positive_listings = [specimen for specimen in listings if specimen.get("physicalObservation")]
    if not cards:
        state = "needs-evidence"
    elif positive_listings:
        state = "positive-observation"
    else:
        state = "terminal"
    return {
        "state": state,
        "progress": {
            "frozenBaselineCardCount": len(cards),
            "listingSpecimenCount": len(listings),
            "positiveListingCount": len(positive_listings),
            "catalogueExpansion": 0,
        },
    }


EVALUATORS = {
    "physical": physical_state,
    "evidence": evidence_state,
    "discovery": discovery_state,
    "news-promo": news_promo_state,
    "tcgdex": tcgdex_state,
    "absence": absence_state,
    "cardmarket": cardmarket_state,
}


def _next_replay_run_id(now: dt.datetime, retained_run_ids: set[str]) -> str:
    candidate = now.astimezone(dt.timezone.utc).replace(microsecond=0)
    latest = max(retained_run_ids, default=None)
    if latest and candidate.strftime("%Y%m%dT%H%M%SZ") <= latest:
        candidate = dt.datetime.strptime(latest, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=dt.timezone.utc
        ) + dt.timedelta(seconds=1)
    run_id = candidate.strftime("%Y%m%dT%H%M%SZ")
    while run_id in retained_run_ids:
        candidate += dt.timedelta(seconds=1)
        run_id = candidate.strftime("%Y%m%dT%H%M%SZ")
    return run_id


def _next_discovery_run_id(
    now: dt.datetime, source_run_ids: set[str], card_run_ids: set[str],
) -> str:
    """Keep one discovery-cycle ID newer than both immutable run streams."""
    return _next_replay_run_id(now, source_run_ids | card_run_ids)


def _retained_discovery_run_ids() -> tuple[set[str], set[str]]:
    def retained(directory: pathlib.Path) -> set[str]:
        return {
            path.name for path in directory.iterdir()
            if path.is_dir() and re.fullmatch(r"\d{8}T\d{6}Z", path.name)
        }

    return retained(SOURCE_RUNS), retained(CARD_RUNS)


def _discovery_replay_command(
    source_run_id: str, now: dt.datetime | None = None,
    reserved_run_ids: set[str] | None = None,
) -> list[str]:
    source_runs, card_runs = _retained_discovery_run_ids()
    replay_id = _next_discovery_run_id(
        now or dt.datetime.now(dt.timezone.utc),
        source_runs | (reserved_run_ids or set()), card_runs,
    )
    return ["scripts/card_discovery.py", "--replay-from-run", source_run_id, "--run-id", replay_id]


def _source_adapter_replay_command(
    source_run_id: str, now: dt.datetime | None = None,
    reserved_run_ids: set[str] | None = None,
) -> list[str]:
    source_runs, card_runs = _retained_discovery_run_ids()
    replay_id = _next_discovery_run_id(
        now or dt.datetime.now(dt.timezone.utc),
        source_runs | (reserved_run_ids or set()), card_runs,
    )
    return ["scripts/source_adapters.py", "--replay-from-run", source_run_id,
            "--run-id", replay_id]


def _discovery_replay_commands(
    card_source_run: str | None, now: dt.datetime | None = None,
    include_live: bool = False, source_adapter_run: str | None = None,
) -> list[list[str]]:
    commands = []
    reserved: set[str] = set()
    if source_adapter_run:
        source_command = _source_adapter_replay_command(source_adapter_run, now, reserved)
        commands.append(source_command)
        reserved.add(source_command[-1])
    if card_source_run:
        card_command = _discovery_replay_command(card_source_run, now, reserved)
        commands.append(card_command)
        reserved.add(card_command[-1])
    commands.append(["scripts/completeness_gate.py"])
    if include_live:
        commands.append(_discovery_refresh_command(now, reserved))
    return commands


def _discovery_refresh_command(
    now: dt.datetime | None = None, reserved_run_ids: set[str] | None = None,
) -> list[str]:
    source_runs, card_runs = _retained_discovery_run_ids()
    run_id = _next_discovery_run_id(
        now or dt.datetime.now(dt.timezone.utc),
        source_runs | (reserved_run_ids or set()), card_runs,
    )
    return ["scripts/discovery_cycle.py", "--refresh", "--run-id", run_id]


def _stale_discovery_run(loop_id: str, current: dict[str, Any]) -> str | None:
    progress = current["progress"]
    if loop_id != "discovery" or progress.get("stagingMatchesCanonicalInputs"):
        return None
    return progress.get("cardReplayRun")


def _stale_source_run(loop_id: str, current: dict[str, Any]) -> str | None:
    progress = current["progress"]
    if loop_id != "discovery" or progress.get("sourceRecordsCurrent", True):
        return None
    return progress.get("sourceReplayRun")


def _discovery_cycle_stop_reason(
    current: dict[str, Any], after: dict[str, Any], terminal_states: set[str],
) -> str | None:
    """Return a stop reason, or None when the bounded loop should continue."""
    if after["state"] in terminal_states:
        return f"state={after['state']}"
    if after["progress"] == current["progress"]:
        return "no-metric-change"
    return None


def _has_discovery_replay(
    loop_id: str, card_run: str | None, source_run: str | None,
) -> bool:
    return loop_id == "discovery" and bool(card_run or source_run)


def _should_skip_terminal_state(
    loop_id: str, state: str, terminal_states: set[str], include_live: bool,
) -> bool:
    if state not in terminal_states:
        return False
    return not (include_live and (
        loop_id == "discovery" or state in {"needs-refresh", "needs-source"}
    ))


def run_cycle(
    loop_id: str, lane: str, cycle_id: str, include_live: bool, dry_run: bool,
    replay_from_run: str | None = None,
    completeness_is_current: bool = True,
    source_replay_from_run: str | None = None,
    live_refresh_required: bool = False,
) -> dict[str, Any]:
    if dry_run:
        return {"status": "not-run", "reason": "dry-run", "output": ""}
    return _run_command_sequence(
        _cycle_commands(
            loop_id, lane, cycle_id, include_live, replay_from_run,
            completeness_is_current, source_replay_from_run=source_replay_from_run,
            live_refresh_required=live_refresh_required,
        )
    )


def _cycle_commands(
    loop_id: str, lane: str, cycle_id: str, include_live: bool,
    replay_from_run: str | None, completeness_is_current: bool = True,
    now: dt.datetime | None = None, source_replay_from_run: str | None = None,
    live_refresh_required: bool = False,
) -> list[list[str]]:
    if live_refresh_required:
        return [_discovery_refresh_command(now)]
    if _has_discovery_replay(loop_id, replay_from_run, source_replay_from_run):
        return _discovery_replay_commands(
            replay_from_run, now, include_live, source_replay_from_run,
        )
    elif loop_id == "discovery" and not completeness_is_current:
        if include_live:
            # The full refresh rebuilds staging and runs the completeness gate itself.
            return [_discovery_refresh_command(now)]
        return [["scripts/completeness_gate.py"]]
    elif loop_id == "discovery" and include_live:
        return [_discovery_refresh_command(now)]
    command = ["scripts/scoped_regen.py", "--lane", lane, "--run-id", cycle_id]
    if include_live and loop_id == "tcgdex":
        command.append("--include-live")
    return [command]


def _run_command_sequence(commands: list[list[str]]) -> dict[str, Any]:
    outputs = []
    return_code = 0
    for command in commands:
        process = subprocess.run(
            [sys.executable, *command], cwd=ROOT, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        outputs.append(process.stdout)
        return_code = process.returncode
        if return_code:
            break
    return {
        "status": "passed" if return_code == 0 else "failed",
        "returnCode": return_code,
        "command": commands[0] if len(commands) == 1 else commands,
        "output": "\n".join(outputs)[-2000:],
    }


def _discovery_action(progress: dict[str, Any], state: str | None = None) -> str:
    if state == "terminal":
        return "complete"
    source_stale = not progress.get("sourceRecordsCurrent", True)
    staging_stale = not progress.get("stagingMatchesCanonicalInputs", True)
    if (
        source_stale and not progress.get("sourceReplayRun")
        or staging_stale and not progress.get("cardReplayRun")
    ):
        return "live-acquisition-required"
    if source_stale and staging_stale:
        return "reproject-stale-staging"
    if source_stale:
        return "reproject-source-staging"
    if staging_stale:
        return "reproject-staging"
    return "reconcile-to-release-or-record-open-decision"


def _discovery_review_files(progress: dict[str, Any], state: str | None = None) -> str:
    if state == "terminal":
        return "none"
    review_files = []
    if not progress.get("sourceRecordsCurrent", True):
        review_files.append("verification/source_adapter_staging.json")
    if not progress.get("stagingMatchesCanonicalInputs", True) or not review_files:
        review_files.append("verification/card_discovery_staging.json")
    return ",".join(review_files)


def _discovery_summary(
    loop_id: str, progress: dict[str, Any], state: str | None = None,
) -> str:
    if loop_id != "discovery":
        return ""
    return (
        f" newCandidates={progress.get('newCandidateRecords', 0)}"
        f" stagedCandidates={progress.get('stagingCandidateRecords', 0)}"
        f" stagingCurrent={progress.get('stagingMatchesCanonicalInputs')}"
        f" action={_discovery_action(progress, state)}"
        f" review={_discovery_review_files(progress, state)}"
    )


def main() -> int:
    manifest = read_json(MANIFEST)
    loops = {loop["id"]: loop for loop in manifest["loops"]}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loop", required=True, choices=sorted(loops))
    parser.add_argument("--run-id", help="pin a loop run ID for replay or test")
    parser.add_argument("--max-cycles", type=int, default=3)
    parser.add_argument("--include-live", action="store_true", help="allow discovery/TCGdex network refresh")
    parser.add_argument("--dry-run", action="store_true", help="evaluate and report without running a lane")
    parser.add_argument("--out", type=pathlib.Path,
                        default=ROOT / "verification" / "cache" / "workflow-loops")
    args = parser.parse_args()
    if args.max_cycles < 1:
        parser.error("--max-cycles must be positive")
    run_id = args.run_id or f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{args.loop}"
    if not RUN_ID.fullmatch(run_id):
        parser.error("--run-id contains unsupported characters")
    loop = loops[args.loop]
    before = EVALUATORS[args.loop]()
    cycle_reports: list[dict[str, Any]] = []
    skipped: list[str] = []
    stop_reason = "max-cycles"
    current = before

    for number in range(1, args.max_cycles + 1):
        if _should_skip_terminal_state(
            args.loop, current["state"], set(loop["terminal"]), args.include_live,
        ):
            stop_reason = f"state={current['state']} requires external input or is terminal"
            skipped.append(stop_reason)
            break
        cycle_id = f"{run_id}-c{number}"
        replay_from_run = _stale_discovery_run(args.loop, current)
        source_replay_from_run = _stale_source_run(args.loop, current)
        completeness_is_current = current["progress"].get("completenessMatchesInputs", True)
        progress = current["progress"]
        live_refresh_required = args.include_live and (
            not progress.get("sourceRecordsCurrent", True) and not source_replay_from_run
            or not progress.get("stagingMatchesCanonicalInputs", True) and not replay_from_run
        )
        result = run_cycle(
            args.loop, loop["lane"], cycle_id, args.include_live, args.dry_run,
            replay_from_run=replay_from_run,
            completeness_is_current=completeness_is_current,
            source_replay_from_run=source_replay_from_run,
            live_refresh_required=live_refresh_required,
        )
        if result["status"] == "not-run":
            skipped.append(result["reason"])
            stop_reason = result["reason"]
            cycle_reports.append({"cycle": number, "before": current, "lane": result})
            break
        after = EVALUATORS[args.loop]()
        cycle_reports.append({"cycle": number, "before": current, "after": after, "lane": result})
        if result["status"] == "failed":
            stop_reason = "lane-failed"
            current = after
            break
        cycle_stop_reason = _discovery_cycle_stop_reason(
            current, after, set(loop["terminal"]),
        )
        if cycle_stop_reason:
            stop_reason = cycle_stop_reason
            current = after
            break
        current = after

    report = {
        "schema": "snoredex-workflow-loop-run",
        "version": "1.0.0",
        "runId": run_id,
        "loop": args.loop,
        "lane": loop["lane"],
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "states": loop["states"],
        "impactClasses": loop["impactClasses"],
        "maxCycles": args.max_cycles,
        "stateBefore": before,
        "stateAfter": current,
        "cycleCount": len(cycle_reports),
        "stopReason": stop_reason,
        "skippedChecks": skipped,
        "positiveEvidenceRule": manifest["loopContract"]["positiveEvidence"],
        "mergeBoundary": manifest["loopContract"]["mergeBoundary"],
        "cycles": cycle_reports,
    }
    report_path = args.out / f"{run_id}.json" if args.out.suffix != ".json" else args.out
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    candidate_summary = _discovery_summary(args.loop, current["progress"], current["state"])
    print(f"workflow loop: runId={run_id} loop={args.loop} cycles={len(cycle_reports)} "
          f"state={current['state']}{candidate_summary} stop={stop_reason}; report={report_path}")
    return 1 if any(c["lane"].get("status") == "failed" for c in cycle_reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
