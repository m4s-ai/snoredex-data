# Simplified Chinese 30th Celebration — 2026-10-01

The owner supplied the eBay WebP image retained as `source.webp`. The independently acquired PNG
endpoint for the same image key is retained unchanged as `verification/specimens/SPEC-0600.png`.
Both were inspected. `sources.json` distinguishes the supplied WebP, its tested temporary lossless
decoding and the separately acquired PNG bytes; it does not claim equality between the two server
formats. Local Tesseract was unavailable, so text was inspected visually.

The physical card establishes Simplified Chinese 卡比兽, `30th C 095/103 C`, HP160, Aya Kusube,
regulation J, the anniversary logo and Holo. The printed rules and illustration match the existing
Good Sleep / Collapse work. Its CN release identity remains separate from the other localities.
Common is attributed to the owner's explicit Asian-counterpart determination, with visible `C`
retained separately as a printed observation. The card is physically evidenced as released;
no exact launch day or complete finish inventory is asserted.

The earlier 2026-09-10 research gap is closed for this exact card. Korean card identity remains open.
SPEC-0600 avoids SPEC-0599 allocated by the separate Spanish XYPR179 intake branch. Latest fetched
main had SPEC-0598 as its highest ID; compare IDs and hashes again before integration.

Replay: `python verification/fetch_attachment.py --manifest verification/evidence/30th-cn-20261001/manifest.json`
then `python verification/passes/admit_30th_cn_20261001.py` and `python scripts/regen.py`.
The admission pass preserves all unrelated graph entities and is idempotent.
