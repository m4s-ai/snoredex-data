<!-- doc: role=review remediation and merge conservation; stage=reference -->
# Review remediation and main integration

Reviewed head: e83dc0090c1acbb8e7e5a9df87df18c72a6fb845.
Integrated main: 9aa90fe (PRs #391 and #393).

- Review 4063196962: SPEC-0549 now links to SPEC-0548 through sameCardAs. Two listing angles share the sleeved card, sleeve creases and Pikachu marker. The canonical manifest importer applied the link without changing photographs; identity-only finish uncertainty remains unchanged.
- Review 4063362153: shared graph snapshot maximum includes specimen recordedAt values, including identity-only images. The regression first reproduced a later 2031-02-03 identity observation leaving the graph dated 2026-09-21. Tests require the later date, repeat projection stability, and preservation of an even newer graph date.
- Main introduced unrelated English/German MEW specimens as SPEC-0528/0529. The PR's Korean s5a 093/070 UR and s1H 070/060 HR observations were migrated to SPEC-0552/0553 before combining stores. Original photo bytes and SHA-256 values are conserved, and retained intake manifests/source paths follow the new IDs. Main's SPEC-0528/0529 records remain exactly as committed upstream.
- Conflicting generated outputs are regenerated from combined canonical sources. Set-source capability additions and evidence-log additions from both sides are preserved. The authoritative graph retains its reviewed base and reconstructs only the projector-owned physical slice.

All pre-merge PR specimen image hashes were compared with their post-migration records; every upstream main specimen record was compared exactly. No owner attestation, language identity, physical finish, or evidence photograph was dropped. This integration does not authorize merge, readiness or issue closure: PR #390 stays draft.

## Draft-only item ID migration

The specimen-derived IDs below were not merged or deployed. Main IDs are retained unchanged:

| Card | Previous draft item | Replacement draft item |
|---|---|---|
| Korean s5a 093/070 | item-ebfae9f0-9c8e-5795-9dfc-b968b70ad4a3 | item-761bf8d5-a2ca-5693-846b-8c374a932673 |
| Korean s1H 070/060 | item-98fb9a9c-1e65-5fa2-a1e2-0f3e0023c3c2 | item-36bb064e-b7da-5403-a6c9-6ee9b7cf4b4c |

A multiset comparison conserved all 1011 release/finish/pattern/marking/distribution/edition/item-kind memberships. Totals remain 770 verified printings, 113 finish candidates and 128 research placeholders. Full regeneration/core checks passed after integration, including the new later-identity-only-date regression. Initial targeted corpus checking before registry regeneration failed on the newly integrated main citation; the full regenerated registry and corpus checks pass.
