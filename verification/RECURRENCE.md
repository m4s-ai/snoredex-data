<!-- doc: role=bounded source-first refresh procedure; stage=task -->
# Recurring source-first discovery loop

The release gate proves the newest retained runs; it never treats a zero result as an absence.
Set/product discovery and card discovery stay independent and each run is immutable.

## Triggers

Run a refresh when a scheduled interval fires, a provider manifest changes, a known Pokémon TCG
release lands, or a maintainer requests a manual source refresh. Use a unique UTC run id:

```console
python scripts/discovery_cycle.py --refresh --run-id 20260821T120000Z
```

The command fetches the official set/product slices and card slices, retains their raw responses,
diffs them through the existing adapters, and writes `verification/completeness_gate.json`. It does
not commit, merge, or publish. Review every `newCandidate`, `ambiguous`, `needsEvidence`, and gap
delta before opening a PR. A failed request remains a source failure in the immutable run; it is
not an empty catalogue.

Canonical staging uses the newest complete retained run compatible with the acquisition contract
and scoped capability pin. Failed, incomplete, empty, and incompatible runs stay retained but do
not displace it. Replay preserves the selected source run's bytes and retrieval metadata while
rendering through the current reviewed projection contract and capability state.

For a local or CI check without network access:

```console
python scripts/discovery_cycle.py --check
```

Check mode is read-only and cannot be combined with refresh, replay, acceptance, or another write
action.

The gate records both run ids, both coverage versions, raw-record hashes, the graph counts and the
explicit Asia/non-Asia gap states. `terminalState=complete` means the bounded inputs balance; it
does not claim a complete historical or all-locality universe.

## Release decision

`python scripts/regen.py --check` runs the same gate used by CI. Publish only when it is green and
all new or changed records have a visible reconciliation state. A provider returning zero rows,
an incomplete page set, or a changed source capability fails closed and must be retried or named as
`needs-evidence`/`blocked-by-source`.
