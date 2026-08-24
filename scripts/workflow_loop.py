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
MANIFEST = ROOT / "verification" / "workflow_loop_manifest.json"
EVIDENCE = ROOT / "verification" / "evidence_semantics.json"
SOURCE_ADAPTERS = ROOT / "verification" / "source_adapters.json"
CARD_ADAPTERS = ROOT / "verification" / "card_discovery_adapters.json"
SOURCE_RUNS = ROOT / "verification" / "runs" / "source-adapters"
CARD_RUNS = ROOT / "verification" / "runs" / "card-discovery"
SNAPSHOT = ROOT / "verification" / "finish_tcgdex_snapshot.json"
CANDIDATE = ROOT / "verification" / "cache" / "finish-tcgdex" / "refresh-candidate.json"
ADJUDICATIONS = ROOT / "verification" / "owner_adjudications.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SET_SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
CARDMARKET_BASELINE = ROOT / "legacy-cardmarket-baseline.json"
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_manifests(directory: pathlib.Path) -> list[dict[str, Any]]:
    paths = sorted(directory.glob("*/manifest.json"), key=lambda path: path.stat().st_mtime)
    if not paths:
        return []
    return [read_json(paths[-1])]


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


def discovery_state() -> dict[str, Any]:
    source = latest_manifests(SOURCE_RUNS)
    cards = latest_manifests(CARD_RUNS)
    gaps = read_json(SOURCE_ADAPTERS)["gaps"] + read_json(CARD_ADAPTERS)["gaps"]
    failures = sum(len(manifest.get("failures", [])) for manifest in source + cards)
    statuses = [manifest.get("status") for manifest in source + cards]
    blocked = sum(gap.get("terminalState") == "blocked-by-source" for gap in gaps)
    needs_source = sum(gap.get("terminalState") == "needs-evidence" for gap in gaps)
    if not source or not cards:
        state = "candidate"
    elif any(status != "complete" for status in statuses):
        state = "retained"
    elif blocked:
        state = "blocked-by-source"
    elif needs_source:
        state = "needs-source"
    else:
        state = "terminal"
    return {
        "state": state,
        "progress": {
            "sourceRun": source[0].get("runId") if source else None,
            "cardRun": cards[0].get("runId") if cards else None,
            "sourceStatus": source[0].get("status") if source else None,
            "cardStatus": cards[0].get("status") if cards else None,
            "failures": failures,
            "blockedGaps": blocked,
            "needsSourceGaps": needs_source,
            "totalGaps": len(gaps),
        },
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


def run_cycle(loop_id: str, lane: str, cycle_id: str, include_live: bool, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"status": "not-run", "reason": "dry-run", "output": ""}
    if loop_id == "discovery" and include_live:
        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        command = ["scripts/discovery_cycle.py", "--refresh", "--run-id", timestamp]
    else:
        command = ["scripts/scoped_regen.py", "--lane", lane, "--run-id", cycle_id]
        if include_live and loop_id == "tcgdex":
            command.append("--include-live")
    process = subprocess.run(
        [sys.executable, *command], cwd=ROOT, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    return {
        "status": "passed" if process.returncode == 0 else "failed",
        "returnCode": process.returncode,
        "command": command,
        "output": process.stdout[-2000:],
    }


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
        live_discovery_refresh = (
            args.include_live
            and args.loop == "discovery"
            and current["progress"].get("needsSourceGaps", 0) > 0
        )
        if current["state"] in loop["terminal"] and not (
            live_discovery_refresh
            or (args.include_live and current["state"] in {"needs-refresh", "needs-source"})
        ):
            stop_reason = f"state={current['state']} requires external input or is terminal"
            skipped.append(stop_reason)
            break
        cycle_id = f"{run_id}-c{number}"
        result = run_cycle(args.loop, loop["lane"], cycle_id, args.include_live, args.dry_run)
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
        if after["state"] in loop["terminal"]:
            stop_reason = f"state={after['state']}"
            current = after
            break
        if after["progress"] == current["progress"]:
            stop_reason = "no-metric-change"
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
    print(f"workflow loop: runId={run_id} loop={args.loop} cycles={len(cycle_reports)} "
          f"state={current['state']} stop={stop_reason}; report={report_path}")
    return 1 if any(c["lane"].get("status") == "failed" for c in cycle_reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
