<!-- doc: role=standalone Malie package usage and limits; stage=task -->
# Malie pilot package

Profile: **`snoredex-malie-sv-pilot/1`**, based on the pinned Malie draft dated
2024-05-20. This is an additional export from Snoredex, not a replacement for its
identity, evidence or collection model.

| File | Meaning |
|---|---|
| [cards.json](cards.json) | Three supported physical printings: English MEW 143 non-holo/reverse and German MEW 143 non-holo. |
| [report.json](report.json) | All six selected inputs, stable item/release/printing IDs, physical dimensions, field sources, unresolved reasons and input/card/profile digests. |
| [profile.json](profile.json) | Exact finite selection, vocabulary, mapping rules and upstream version/digest pin. |

Keep all three files together. The cards array alone loses stable physical identity
and the explanation of omitted inputs. Equal card contents must not be deduplicated:
the report's IDs identify printings; an array position or payload hash does not.

## Read the bundle offline

Copy the standalone [consumer script](../../scripts/malie_consumer.py) and this
three-file bundle to any directory with Python 3.11 or later. Run:

```console
python malie_consumer.py path/to/exports/malie
```

The script uses only the Python standard library and reads only these three files.
It checks canonical JSON, file/card/complete-identity hashes, selected-input accounting, ID/locality
joins and supported physical scope, then prints JSON with cards attached to their
stable IDs. It preserves all deferred entries and reasons. JSON output uses ASCII
escapes for accents so Windows pipes remain portable; decoding the JSON restores
the exact Unicode text. It does not contact upstream or load internal graph files.

The expected pilot result is **6 selected, 3 exported, 2 needs-evidence and 1
outside-profile**. The two SVP variants retain distinct printing/distribution/stamp
identities and explicit evidence/mapping gaps. The German Jungle research entry
has no fabricated physical ID. Missing evidence never means a card does not exist.

## Reproduce and bind a release

In the repository, use `python scripts/malie_export.py --write` to generate and
`python scripts/malie_export.py --check` to observe without writes. The normal
`python scripts/regen.py --check` includes the real pilot and corruption checks.
`python verification/test_malie_package.py` runs the copied standalone consumer
against an isolated bundle with independently specified expected IDs and values.

The existing `scripts/publish.py` allowlists the complete bundle and verifies its
integrity against the checked source artifacts. A partial or mixed package fails.
The existing runtime gate manifests (schema 1.1.0) bind all three exact file digests
to the containing commit and compare the Linux/Windows results. They are emitted
after that commit exists, outside deterministic regeneration; no self-referential
commit ID or wall-clock timestamp is inserted into these data files. Deployment
remains the existing separately authorized manual release path.

## Scope and evidence limits

- Only the declared English/German SV pilot is covered. Historical and APAC cards
  are not implicitly supported; a language mapping is not proof of TCGL membership.
- Accepted sources and their grades, dates, field scope and retained-file hashes
  are recorded in the report. Reading this package does not re-examine the original
  source assets or independently prove their claims. Hashes detect inconsistent
  files; they are not an authenticity signature.
- `stage_text` follows the written draft requirement even though the inspected
  upstream reference omits it. No external Malie application has been exercised;
  acceptance demonstrates this documented profile, not universal interoperability.
- Upstream changes require deliberate comparison with the pinned draft/reference,
  a reviewed profile/mapping change and regenerated tests. Never automatically
  overwrite accepted rules or silently remove a selected blocked input.
- A later Malie-oriented internal content model is a separate architectural decision.

The [field and identity contract](../../verification/MALIE-EXPORT.md) explains the
full boundary. [Repository licence](../../LICENSE.md) and source attribution still apply.
