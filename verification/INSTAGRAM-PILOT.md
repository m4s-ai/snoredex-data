# Local Instagram pilot

Install Pillow in the environment used for image preparation. Supply the local photo archive and a
SPEC with documented owner authorship and exactly one verified printing.

```console
python verification/instagram_package.py SPEC-0774 --photos ../snoredex-photos
```

The private output directory `verification/cache/instagram/SPEC-0774/` contains the 4:5 portrait JPEG,
a German caption draft, alt text and a JSON record linking the files, photo hash and exact printing.
The export verifies the archived original by SHA-256. To crop the original, pass `--corners x1 y1 x2 y2 x3 y3 x4 y4` for the full card face, clockwise from top left
after applying the original's EXIF orientation. Leave a small margin around the card edges. With no
corners, the draft shows the whole original. The exporter never enlarges a small crop. Use a new
output directory via `--out` if the inputs have changed.

Use the [YOURLS link pilot](YOURLS-PILOT.md) to check or assign a permanent keyword.

Once the matching entry in `data/social.json` has a verified `shortAlias`, generate a fresh draft.
The full `go.m4s.eu` URL appears in the caption. An unconfigured alias is shown as
`[Kurzlink fehlt]`. Before posting, compare image, caption and alt text against the card, then open
the actual short URL and verify the variant and share image. Confirm fit and cropping in the draft
on the target account. Publish manually and record the Instagram permalink in the same item's
`instagramPosts` array so that the card page and gallery can link back to it.

Run the focused tests with `python verification/test_instagram_package.py`.
