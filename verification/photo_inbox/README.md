<!-- doc: role=private photo inbox for owner phone uploads (#626, #639, #641, #646); stage=task -->

# Private SnoreDex photo inbox (#626, #639, #641, #646)

A small LAN service where the owner hands in their own photos from the phone: the iPhone's DNG
(ProRAW) or JPEG. Every photo here is the owner's own; images found elsewhere go through the regular
specimen intake, never through this inbox. The service keeps the original bytes unchanged, GPS
included, in a private folder outside every Git checkout and publishes nothing. Each photo becomes a
job folder named by the SHA-256 of its bytes, holding `photo.dng` or `photo.jpg` and `job.json` with
`ownPhoto`, the file name, the hash, `receivedAt`, and once described `specimenHint`, `note` and
`describedAt`. A job is its bytes: uploading the same photo again, described or not, is the same job.

**Page (owner decision, 2026-11-24).** The German page (`templates/index.html`, `static/`) has six
tabs instead of one long page: Hochladen, Fotos, Übersicht, Posts, Statistik and Papierkorb. On a phone the
tab bar sits at the bottom with an icon and a label, each tab at least 44 × 44 CSS px. From 48rem
upward it moves beside the title. The tabs follow the WAI-ARIA tabs pattern: automatic activation,
arrow keys, Home and End, one tab stop. Each tab has a hash (`#fotos`) for reload, back and links;
the hash never equals the panel's id, so the browser neither scrolls nor focuses on load. Badges
on the tabs count the photos without details, the drafts ready for Instagram and the trashed ones. The layout follows WCAG 2.2
target sizes and impeccable.style guidance: 17 px body text at 1.5 line height, flat lists with
dividers instead of nested cards, a visible focus outline, and no motion.

Upload and card assignment are separate (owner decision, 2026-11-23). Hochladen takes any number of
photos at once, without details, and sends them one by one with progress and a result per file; a
bad file does not stop the rest. Fotos lists every job, newest first, with a preview (a DNG shows its embedded full-size
preview), a link to a large view, its state ("ohne Angabe", "beschrieben" or "übernommen als
SPEC-nnnn") and a form for the SPEC number, a short note or the exact printing picked from the
catalogue (`itemId`), checked as the single upload always checked them. A printing is picked by
its label, which names everything that tells variants apart (foil pattern, markings, a size other
than standard) and carries the `itemId` where two printings would still read the same. Its views show all jobs,
those without details, the unclassified ones (no printing yet) and those already filed. Saving writes `job.json`
at once; a description can be corrected, the photo never changes. Previews are cached beside the job
as `preview-400.jpg` and `preview-1600.jpg`, upright and without Exif. There is no access code (owner
decision, 2026-11-23): the service is reachable only in the home network.

**Card corners (#657).** A job with a printing gets "Ecken festlegen". The inbox suggests the card
corners with `corners.py`: long straight edges paired into quads of the card's shape, without a
trained model (OpenCV and NumPy; measured in #655, within about 1 % of the card width for one card on
a dark backdrop). The suggestion is cached beside the job as `corners-suggested.json`. With several
cards on the photo the owner taps the right one; with none found, a card-shaped frame in the middle
is the start. The owner drags the four handles on the photo, at least 44 × 44 px, with a loupe beside
the corner under the thumb, or moves them with the arrow keys (Shift for large steps), and sees the
post's title image those corners make. "Ecken freigeben" writes `corners` (four `[x, y]` pairs,
clockwise from top left in the upright full-size photo, the coordinates intake uses) and
`cornersApprovedAt` into `job.json`. The corners must lie inside the photo, run clockwise and frame a
card at least 600 px wide, as the gallery needs. Another printing drops the approval; a filed job
keeps its corners in the catalogue. Without OpenCV the inbox suggests nothing and the owner drags
from the middle.

**Number check (#658).** On approval the inbox reads the collector number from the bottom of the
card face those corners frame, with Tesseract offline (`number_check.py`: two readings, grey and
binarized, in the printing's language and English), and stores `numberCheck` (`result`, `expected`,
`read`, `itemId`, `checkedAt`) in `job.json`. It is a guard, never evidence. A number that contradicts
the printing (`mismatch`, e.g. read `067/080` for `066/080`) shows on the job and stops intake until
the owner corrects the printing or presses "Zuordnung stimmt trotzdem" (`numberConfirmedAt`). A number
it cannot read (`unreadable`), or no Tesseract at all (`unavailable`), stops nothing. A new frame is
read again and needs a new confirmation; another printing drops the check. It cannot tell apart
variants with the same number, and it does not check the set code (read in only 18 % in #655).
On the Homelab the container needs `tesseract-ocr` with the language packs of the collection
(`tesseract-ocr-jpn`, `-deu`, `-chi-sim`, `-kor`, `-fra`, `-ita`, `-spa`, `-ind`, …); `TESSERACT` names
another binary.

**Trash (owner decision, 2026-11-24).** A job that has not been filed as a specimen can be moved to
the trash after a confirmation. The trash is the folder `.trash` inside the data folder: intake reads
only job folders named by their hash, so it never sees it. A trashed job can be restored, or deleted
for good at once after a second confirmation; after 30 days it is deleted for good on its own. A
filed job is never lost here: its archive copy is already in the public photo archive, and taking
back a SPEC is a catalogue change. The same check guards all three ways a job goes: into the trash,
for good from it, and the 30-day sweep. A job intake files after it was trashed stays there until it
is restored. Each check reads the checkout as it is at that moment. Uploading a deleted photo again
makes it a new job. Deleting needs the catalogue (below); without it the inbox cannot tell whether a
photo was filed, so it neither deletes nor empties the trash.

**Overview (#641).** With `--repo` pointing at a checkout of snoredex-data `main`, the page lists
every active printing with the furthest stage its own photo has reached: no own photo, uploaded and
assigned (a job names its `itemId`), filed (an owner specimen is the printing's image on `main`),
online (the published site's catalogue shows that image), ready for Instagram (a verified short link
in `data/social.json`) and posted (an Instagram permalink). A job counts as filed as SPEC-nnnn when
`derive.py` makes exactly that specimen's archived photograph from it. A successful hash is cached
beside the job as `archive.sha256`; a failed derivation is not cached and is tried again. A filed
job takes its SPEC number and its printing from the checkout into `job.json` (owner decision,
2026-11-24), again whenever the checkout reassigns them: the printing whose image that specimen is,
else the one printing its citations name; a specimen cited by several printings leaves the job's own
pick. Views show the printings with an owner photo, those without and every
printing, with a stage filter, a search, the count per stage and statistics by language or set, all
counted from the same rows. The published catalogue is re-read every ten minutes; when the site
cannot be read, nothing counts as online and the page says so. The overview writes nothing to the
repository, the photo archive or the site. Keep the checkout current (`git pull` on `main`).

**Posts (#646, owner decision 2026-11-24).** With `--photos` pointing at a checkout of
snoredex-photos, the Posts tab shows the draft of every printing with a verified short link in
`data/social.json`: the post image, caption, alt text, the open points before posting, and links to
the card page, the short link and the image file. The checkout's own `instagram_package.py` builds
each draft from that checkout, with the cover corners stored in `postCorners`, into `.drafts` inside
the data folder, once per state of the catalogue files. Keep the photo checkout current (`git pull`),
like the catalogue. A carousel shows every image in order, each with its own alt text.

**Posting (#646, owner decisions 2026-11-24).** With `--uploader` pointing at the owner's upload
service and its key in the environment variable `UPLOADER_KEY` (never in a file, the repository
or a log), each draft offers the SnoreDex accounts on Instagram, Facebook and Threads, all
preselected, and a time; the uploader's other accounts never appear and cannot be posted to (owner decision
2026-11-25). The drafts show at once; the send form follows when the uploader names the accounts. Only the owner's
click, after a confirmation, posts: "Jetzt posten" at once, "Einplanen" at the chosen time. The
order freezes the draft the owner saw in `.posts/<SPEC>/` inside the data folder, so a later catalogue
change never alters it; a draft that changed since the page loaded is refused. A queue thread sends
every due order: it uploads the images to the uploader, which serves them to Meta under an
unguessable URL, and starts one job per account. Orders live on disk, so a scheduled post survives a
restart. Every job carries a `clientRef` the uploader deduplicates on, so a restart between sending
and recording never posts twice. The page shows each account's state and permalink; a job that failed
before publishing shows its reason and can be sent again, as a new attempt. A planned order can be
taken back until it goes; a sent post cannot. One order per draft.

**Permalinks into the data.** The inbox writes nothing into the repository. An agent run records the
permalinks of published orders in `data/social.json` (`instagramPosts`, `facebookPosts`,
`threadsPosts`) from the data folder or its read-only share, and opens a data PR that is merged on
green CI (AGENTS.md):

```console
python verification/photo_inbox/permalinks.py I:\
```

A JPEG is decoded completely. A DNG is checked at header level only (a TIFF whose first IFD carries
`DNGVersion`); the intake derives the cleaned public copy from it. Intake takes the described jobs.

| Request | Does |
|---|---|
| `POST /uploads` | one photo as `application/octet-stream`; 201 new, 200 already there |
| `GET /jobs` | every job, newest first |
| `GET /jobs/<id>/preview?size=400\|1600` | the cached preview JPEG |
| `POST /jobs/<id>` | JSON `{"specimen", "note", "itemId"}`: saves the description; another printing drops approved corners |
| `GET /jobs/<id>/corners` | the photo's upright size, the suggested card quads and the approved corners |
| `POST /jobs/<id>/corners` | JSON `{"corners"}`: approves them and reads the number; 400 without printing or for invalid corners, 409 when filed |
| `POST /jobs/<id>/number` | the owner confirms the printing although the number read differs; 400 without a mismatch |
| `GET /jobs/<id>/cover?c=x1,y1,…` | the post's title image from these corners |
| `DELETE /jobs/<id>` | moves an unfiled job to the trash; 409 when filed or without catalogue |
| `GET /trash` | the trashed jobs; anything older than 30 days is deleted first |
| `GET /trash/<id>/preview?size=400\|1600` | the preview of a trashed job |
| `POST /trash/<id>/restore` | puts a trashed job back |
| `DELETE /trash/<id>` | deletes a trashed job for good; 409 when filed or without catalogue |
| `GET /overview` | every active printing with its stage, links and jobs (needs `--repo`) |
| `GET /posts` | the draft of every shared printing (needs `--repo` and `--photos`) |
| `GET /posts/<SPEC>/image?n=1` | that draft's post image, `n` counting the carousel |
| `GET /accounts` | the uploader's SnoreDex accounts on Instagram, Facebook and Threads (needs `--uploader`) |
| `POST /posts/<SPEC>/order` | JSON `{"draft", "accounts", "at"}`: posts now (`at` null) or at that time; 409 for a changed draft or a second order |
| `DELETE /posts/<SPEC>/order` | takes back a planned order; 409 once it was sent |
| `POST /posts/<SPEC>/retry` | JSON `{"account"}`: sends a failed job again |

## Run

```console
pip install -r verification/photo_inbox/requirements.txt
python verification/photo_inbox/app.py --data-dir <private folder outside Git> --host 0.0.0.0 --repo <checkout of main> --photos <checkout of snoredex-photos> --uploader <uploader base URL>
```

Set `UPLOADER_KEY` in the environment for `--uploader`.

Without `--host` the service listens on loopback only; `--host 0.0.0.0` (or a reverse proxy on the
Homelab) makes it reachable in the home network on port 8765 (`--port`). Uploads are limited to
200 MB, and JPEGs to 60 megapixels.

## Container on the Homelab

`docker/` holds the manifest the Homelab runs:

- `Dockerfile` builds one image from the repository root.
  - **Contents:** Python 3.12, the inbox's packages (OpenCV and NumPy for the corners), Tesseract with
    the collection's languages for the number check, and git.
  - **Repository code:** the image holds only the code the inbox runs or imports.
    `Dockerfile.dockerignore` keeps data, images and evidence out.
  - **User:** it runs as an unprivileged user whose `PUID` and `PGID` match the owner of the mounted
    folders.
- `compose.yaml` runs two services: `inbox`, and `sync`, which `git pull`s both checkouts every ten
  minutes, fast-forward only.
  - `inbox` gets the private data folder at `/data`, and the checkouts of snoredex-data and
    snoredex-photos (branch `main`) read-only under `/checkouts`.
  - The inbox notices a changed catalogue by itself.
  - A change to the inbox's own code or requirements needs a rebuild.
- `env.example` lists the settings. Copy it to `.env` beside `compose.yaml`; Git ignores that file. It
  holds the three host paths, `PUID`/`PGID`, the port and, for posting, `UPLOADER_URL` and
  `UPLOADER_KEY`. The key reaches the inbox only through the environment.

```console
git clone https://github.com/m4s-ai/snoredex-data /srv/snoredex/snoredex-data
git clone https://github.com/m4s-ai/snoredex-photos /srv/snoredex/snoredex-photos
cd /srv/snoredex/snoredex-data/verification/photo_inbox/docker
cp env.example .env        # then set the paths, PUID/PGID and the uploader
docker compose up -d --build
```

The image is built from the checkout the compose file sits in. A merge that changes the inbox
(`scripts/`, `verification/photo_inbox/`, `verification/*.py`) needs an update on the Homelab, which
the owner or Hermes runs, never an agent (AGENTS.md). For it, run `sh update.sh` in that folder
instead of the last line above. It pulls the checkout, then rebuilds and restarts with
the commit the image is built from, and prints that commit.

Then check the version line at the foot of the page (also as JSON under `/version`, #666). After an
update it must name the merged commit and say `Code aktuell`. It shows:

- **Code:** the commit the image was built from, and when. Without `update.sh` it says `unbekannt`.
- **Katalog** and **Fotos:** the commit of each mounted checkout. Their dates show whether `sync`
  pulls.
- **Neu bauen:** the line warns `Anderer Eingangs-Code im Checkout: neu bauen` when the synced
  checkout carries other inbox code (`scripts/`, `verification/photo_inbox/`, `verification/*.py`)
  than the running image. It says `Code aktuell` when it does not.

The workflow `Inbox image` builds the image on every pull request that touches the inbox. It checks
Tesseract's languages and the number guard's tests, starts the inbox against the repository and runs
`docker/smoke.py` inside it. The smoke test covers the page, the catalogue, suggested corners, a
printed number read, and a version line naming the commit just built.

## Intake access

The inbox runs as a Docker container on the Homelab with the data folder as a bind mount. Intake
reads the jobs through a read-only SMB share of that folder, `snoredex-inbox`, hidden from browsing
and open to the owner's user only (owner decision, 2026-11-23). The host firewall must allow TCP 445
from the home network; a Docker port passes the firewall differently, so the page being reachable
does not prove the share is. On the Windows intake machine, store the login once (the command asks
for it) and map the share; where PowerShell does not find the commands, call them from `System32`:

```console
cmdkey /add:<host> /user:<owner user> /pass
net use I: \\<host>\snoredex-inbox /persistent:yes
```

Raw files are read from the share and never copied into a repository.

## Archive copy

`derive.py` turns one job into the photograph intake files (snoredex-specimen-intake, step 4):

```console
python verification/photo_inbox/derive.py I:\<job> <photo checkout>\verification\specimens\SPEC-nnnn.jpg
```

A DNG gives its embedded full-size preview, the camera's own rendering; a JPEG gives itself. The
image data is copied, never re-encoded. Only the orientation tag and the ICC colour profile stay:
GPS, XMP, maker data and any further frame (the HDR gain map) go. The script refuses unless the copy
decodes pixel-identical to its source and carries no location, never overwrites a file, and prints
the hashes and size the specimen record names. It reproduces SPEC-1111, the first inbox photo,
byte for byte. A DNG without a full-size JPEG preview is refused and needs a raw decoder instead.

## Filing a job without an agent (#656)

`intake.py` files one job as an owner specimen, without an agent and without an AI service (owner
decision, 2026-11-24, #654):

```console
python verification/photo_inbox/intake.py I:\<job> --photos <photo checkout> [--pr]
```

- It needs the job's printing (`itemId`) and its approved card corners (`corners` in `job.json`, or
  `--corners` with eight pixel values clockwise from top left in the upright photo). Without them it
  stops and says why. It also stops on a number check that contradicts the printing until the owner
  has confirmed it (#658).
- The owner's assignment is an owner attestation of the printing's identity. The record claims that
  (`ownerAttestedFields: ["identity"]`, dated by the assignment) and nothing read from the face: no
  finish, edition or marking, neither read nor copied from the printing. The printing's source row
  cites it with the provider `owner-attestation`.
- The photo's archive copy comes from `derive.py`. Bytes that are already registered stop the run
  with their SPEC. A copy that an interrupted run pushed but never recorded is found again by its bytes
  and reused. Otherwise the next number after `origin/main` and the photo archive is reserved by pushing
  the copy; when another intake pushed first, the run takes the next one.
- Preview and gallery images come from the approved corners, exactly as the specimen-intake skill
  makes them; they replace the item's image unless that already is an owner photograph, which the item
  keeps. A new share row records the corners as `postCorners`.
- Then `check.py`, `check.py --photos` and `regen.py`, and a commit on `intake/SPEC-nnnn`. `--pr` pushes
  it and opens the pull request, which is merged on green CI (AGENTS.md). `--dry-run` writes nothing.

## Intake run on the Homelab (#659)

`runner.py` runs the whole chain in the inbox container, without an agent. It starts from the
**Übernehmen** button on a job, or each night at 03:00 UTC for every job that is ready, failed runs
included. A job is ready when it has its printing, approved corners and no unconfirmed number mismatch,
and is not filed yet.

1. `intake.py` files the job in the run's own clones (`.work/` in the data folder). The run then pushes
   the branch and opens its pull request.
2. The pull request is merged once every check is green; a red check stops the run with its link.
3. `Publish site` runs on main.
4. `Provision Snoredex short links` runs for the printing; its verified alias is read from the run's
   artifact.
5. A second pull request records the alias in `data/social.json` and is merged on green CI. Once `sync`
   has pulled main, the Posts tab shows the draft.

The job shows each step, and when a step fails, the reason. The run writes every finished step to
`intake-run.json` beside the job, so a new start, by the button or the night, carries on where it
stopped:

- `intake.py` finds its archive copy again by its bytes.
- An open pull request is reused, and a merged one is not merged again.
- An alias already on main is not recorded again.

A restart of the container marks a cut-off run as interrupted.

An approval holds for exactly one printing (owner decision D01, 2026-11-25, #672). Queuing, by the
button or the night, freezes the photo's hash, its printing and its corners in `intake-run.json`:

- Intake starts only when the job still has the frozen printing and corners; otherwise the run stops
  before anything is filed.
- Before the short link and again before the alias pull request, the run checks on main that its SPEC
  is filed for the frozen printing. A different or no unique printing stops the run there.
- A run from before the freeze takes the printing main filed its SPEC for.
- The page closes the printing field and the corners from the queue on. A run that stops before filing
  opens them again, and the next start freezes the corrected approval. Once the SPEC is filed they stay
  closed: a wrong assignment is then corrected in the catalogue.

Access stays in the Homelab's environment only (owner decision, 2026-11-24, #654):

- `INTAKE_GITHUB_TOKEN`: a fine-grained token for snoredex-data only (contents, pull requests and actions
  read/write, checks read).
- `PHOTOS_DEPLOY_KEY_FILE`: a deploy key with write access to snoredex-photos only, mounted read-only.

Without both, the page shows no button and nothing runs at night. The token reaches git through an
askpass script that reads it from the environment, never from a file or a command line. The run
commits as `SnoreDex inbox` with a GitHub noreply address.

## Check

```console
pip install -r requirements.txt -r verification/photo_inbox/requirements.txt
python verification/photo_inbox/test_app.py
python verification/photo_inbox/test_intake.py --photos <photo checkout>
python verification/photo_inbox/test_number_check.py
python verification/photo_inbox/test_runner.py
```

`test_runner.py` drives the intake run against local Git remotes and a stand-in GitHub. It covers the
whole chain, a restart after a failed step without a second filing, pull request or merge, red CI, a
refused job, an alias already on main, a run cut off by a restart, and the page's button. It also
covers the frozen approval: a printing changed after filing, a SPEC main files for another printing,
a run from before the freeze, corners changed between the queue and intake, and the page's lock.

`test_number_check.py` turns the misreadings seen in #655 into verdicts and checks when the guard
stops intake. `test_app.py` reads a printed number on a synthetic card when Tesseract is installed
(match, a wrong printing as mismatch, confirmation, a new frame read again) and says so when it is not.

`test_intake.py` files a synthetic phone photo (sideways, with GPS) for a printing with and one
without an owner photo and runs every `check.py` rule on the result; it refuses a job without printing
or corners and a photo already filed, finds an orphaned archive copy, lets two intakes race for a
number, and with the photo archive rebuilds SPEC-1125's gallery and preview files byte for byte.

It covers uploads without details (a JPEG with GPS kept privately, byte for byte; DNGs in both byte
orders; a plain TIFF, a truncated DNG header, non-photo and truncated JPEG files refused; the size
and pixel limits; repeats), the dashboard (newest first, previews without Exif or GPS, a DNG without
an embedded preview, invalid and corrected descriptions, a described photo uploaded again), the
trash (no delete without catalogue or of a filed job, restore, a re-upload, delete for good, emptied
after 30 days), the overview with test data for every stage (an unreadable site counts nothing as
online), a restart, an inbox inside a Git checkout, and in a phone-sized Chromium a bulk upload with
one bad file, a description with its printing, the views, counts and statistics, and delete,
restore and delete for good, the card corners (a suggestion within 2 % on a sideways photo; no
approval without printing, counter-clockwise, too narrow or outside the photo; the title image;
a new note keeps, another printing drops and a filed job refuses the approval; in the browser the
handle size, keyboard steps, the loupe, a drag and the approval), the Posts tab with a stand-in exporter (built once per catalogue state,
a failed draft with its reason) and a stand-in uploader (accounts preselected, a dismissed confirmation
posts nothing, a plan taken back; a changed draft, a time without zone and a second order refused;
an unreachable uploader retried, a resend after a crash deduplicated, a failed job sent again; the
permalinks recorded once per platform), and the archive copy of a phone-like DNG and JPEG (location, maker, XMP and
second frame gone; pixels, profile and orientation kept; a DNG without preview refused). It is not
part of `regen.py`, whose gate stays standard-library only.

## Still open

1. Done 2026-11-23: an iPhone 15 Pro ProRAW DNG (DNG 1.6, 12 megapixels) arrived unchanged from
   the phone's photo picker and is readable over the share, hash matching its job.
2. Done 2026-11-23: the first job went through intake as SPEC-1111; `derive.py` now makes that
   archive copy. Next: its Instagram package through #625.
3. Done in #639: bulk upload, the dashboard, "übernommen als SPEC-nnnn" on a job and the trash.
   Done in #641: the overview of every printing.
4. Later in #626: HEIC input, an edited JPEG and its DNG in one job, questions on the job, and
   resuming after an interrupted archive push.

[Upload and import issue](https://github.com/m4s-ai/snoredex-data/issues/626) · [Bulk upload and dashboard](https://github.com/m4s-ai/snoredex-data/issues/639)
