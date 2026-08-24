<!-- doc: role=policy for historical evidence passes; stage=task -->
# Evidence-pass policy

This directory contains historical, issue-specific evidence records. It is not the recurring
workflow. A routine physical-card addition extends the canonical specimen manifest and uses:

```console
python verification/fetch_attachment.py --issue NUMBER --manifest PATH
python verification/fetch_attachment.py --evidence-check
python scripts/regen.py
```

The maintained replacements are the manifest importer, finish projector, authoritative graph
projector, targeted checks, and `scripts/regen.py`. A new Python pass is justified only for a
migration, bulk repair, or data-model change. In particular, the #269 pass remains as historical
provenance but is superseded by the maintained five-specimen/four-printing regression.

Completed passes may move to `verification/archive/passes/` only after their assertions are covered
by a maintained fixture or invariant. The archive is hash-pinned and never edited; no evidence is
deleted during cleanup. Human classification remains mandatory: omitted finish, edition, marking,
or language fields stay omitted, and a missing edition stamp is never evidence of Unlimited.
