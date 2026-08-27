---
name: snoredex-specimen-intake
description: File physical Snoredex card or seller-listing photographs as stable specimen evidence and project their supported observations. Use for local images, issue attachments, scans, or listing photos; not for source pages without a card image.
---

# Snoredex specimen intake

Turn physical-card image evidence into a stable, checkable specimen record without asserting anything the image cannot establish.

## Required context

Read [CLAUDE.md](../../../CLAUDE.md), [HANDOVER.md](../../../HANDOVER.md), the complete [verification playbook](../../../verification/RESUME.md), [FINISH_SOURCES.md](../../../verification/FINISH_SOURCES.md), and the physical-evidence path in [WORKFLOW-MAP.md](../../../WORKFLOW-MAP.md).

## Workflow

1. Inspect the original image at sufficient resolution. Identify only visible facts: card identity, printed language/locality markers, finish or foil pattern, stamps or markings, distribution marks, and size cues.
2. Match or create the stable `SPEC-nnnn` record through the canonical manifest workflow. Do not replace a specimen with prose or reuse a neighbouring specimen's authority.
3. For repository issue attachments, prepare one reviewed observation manifest and run `python verification/fetch_attachment.py --issue <number> --manifest <path>`. For a local or already reachable image, use the documented `--specimen ... --from ...` form.
4. Preserve the stable issue or listing URL as provenance and the imported byte hash as integrity evidence. File seller photographs as third-party-held specimens, never as a bare marketplace link.
5. Record `physicalObservation` only for facts the image supports. Leave finish or other fields unset when glare, resolution, crop, or missing card surfaces prevent a reliable reading.
6. Run `python scripts/workflow_loop.py --loop physical --max-cycles 3` and inspect its stop reason. Then run `python scripts/scoped_regen.py --lane physical-evidence`.
7. Run `python scripts/regen.py`, review specimen, finish, graph, collector, and publication-allowlist effects, and report any evidence still missing.

If the original bytes cannot be obtained or safely matched to a specimen, stop with the exact missing input. A missing photograph is not evidence of absence.
