# Local Instagram pilot

Install Pillow in the environment used for image preparation. Supply the local photo archive and a
SPEC with documented owner authorship and exactly one verified printing.

```console
python verification/instagram_package.py SPEC-0774 --photos ../snoredex-photos
```

The private output directory `verification/cache/instagram/SPEC-0774/` contains the 4:5 portrait JPEG,
an English caption draft, alt text and a JSON record linking the files, photo hash and exact printing.
The @SnoreDex account is kept in English (owner decision, 2026-11-23). A localized card name joins
Snorlax and never replaces it, for example `カビゴン (Snorlax)`.

The caption ends with at most five hashtags, Instagram's limit per post, in the caption rather than a
comment: `#Snorlax #PokemonTCG #PokemonCards`, then Snorlax's local name when the card carries one
(`#カビゴン`, `#Relaxo`), the set when its name makes a short Latin tag (`#GymHeroes`) and
`#ReverseHolo`, in that order until five. Hashtags label a post for collectors; they do not raise its
reach. The searchable words are the card facts in the caption itself.

The export verifies the archived original by SHA-256. Pass `--corners x1 y1 x2 y2 x3 y3 x4 y4` at the
card face's own edges, clockwise from top left after applying the original's EXIF orientation. The
cover then frames the card at about 60 % of the width, nudged down to keep its stand in view, and
darkens everything around the card in a soft vignette, in the style of the owner's edited holder
photos. The card's own pixels, foil included, stay as photographed. With no corners, the draft shows
the whole original on a dark canvas. Every cover carries a small `@SnoreDex` watermark at the bottom
right. The exporter never enlarges a small crop. Use a new output directory via `--out` if the inputs
have changed.

## Use an edited photo of the card on its stand

Pass `--owner-feed-jpeg` only for an edited JPEG you photographed and have checked against the
exact printing for the SPEC. Use `--feed-alt` to describe the visible card, stand and any important
details in that image. The command below assumes a new, locally prepared photo of SPEC-0774.

```console
python verification/instagram_package.py SPEC-0774 --photos ../snoredex-photos --owner-feed-jpeg halter.jpg --feed-alt "Chinese Snorlax card 061/S-P on a card stand against a dark background." --out verification/cache/instagram/SPEC-0774-halter
```

This option preserves the edited composition, adds padding when needed, adds the watermark, and
writes a 1080 × 1350 sRGB JPEG without EXIF or XMP. Use `--corners` only with the original-photo path. The archive still
supplies the verified specimen and its hash. The private manifest also records the edited JPEG's
hash and your confirmation that it shows the same printing. Keep any DNG originals in your private
photo archive. Review legibility, borders and foil in the phone draft before posting.

Use the [YOURLS link pilot](YOURLS-PILOT.md) to check or assign a permanent keyword.

Once the matching entry in `data/social.json` has a verified `shortAlias`, generate a fresh draft.
The full `go.m4s.eu` URL appears in the caption. An unconfigured alias is shown as
`[short link missing]`. Before posting, compare image, caption and alt text against the card, then open
the actual short URL and verify the variant and share image. Confirm fit and cropping in the draft
on the target account. Publish manually and record the Instagram permalink in the same item's
`instagramPosts` array so that the card page and gallery can link back to it.

Run the focused tests with `python verification/test_instagram_package.py`.
