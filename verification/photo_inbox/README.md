<!-- doc: role=private photo inbox for owner phone uploads (#626, #639, #641, #646); stage=task -->

# Private SnoreDex photo inbox (#626, #639, #641, #646)

A small LAN service where the owner hands in their own photos from the phone: the iPhone's DNG
(ProRAW) or JPEG. Every photo here is the owner's own; images found elsewhere go through the regular
specimen intake, never through this inbox. The service keeps the original bytes unchanged, GPS
included, in a private folder outside every Git checkout and publishes nothing. Each photo becomes a
job folder named by the SHA-256 of its bytes, holding `photo.dng` or `photo.jpg` and `job.json` with
`ownPhoto`, the file name, the hash, `receivedAt`, and once described `specimenHint`, `note` and
`describedAt`. A job is its bytes: uploading the same photo again, described or not, is the same job.

**Page (owner decision, 2026-11-24).** The German page (`templates/index.html`, `static/`) has seven
tabs instead of one long page: Hochladen, Fotos, Übersicht, Posts, Läufe, Statistik and Papierkorb. On a phone the
tab bar sits at the bottom with an icon and a label, each tab at least 44 × 44 CSS px. From 48rem
upward it moves beside the title, in a second row where seven do not fit. The tabs follow the WAI-ARIA tabs pattern: automatic activation,
arrow keys, Home and End, one tab stop. Each tab has a hash (`#fotos`) for reload, back and links;
the hash never equals the panel's id, so the browser neither scrolls nor focuses on load. Badges
on the tabs count the photos without details, the drafts ready for Instagram, the waiting, running and failed intake runs and the trashed ones. The layout follows WCAG 2.2
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
snoredex-photos, the Posts tab lists every printing with a verified short link in
`data/social.json`. Opening one ("Entwurf öffnen") shows its draft: the post image, caption, alt
text, the open points before posting, and links to the card page, the short link and the image file.
The checkout's own `instagram_package.py` builds each draft from that checkout, with the cover
corners stored in `postCorners`, into `.drafts` inside the data folder (#678):
- **The list starts no exporter.** A draft is built when it is opened, and the list shows the drafts
  already built for their current inputs.
- **One draft per fingerprint.** `instagram_package.py SPEC --fingerprint` hashes what the draft is
  made of: its photographs' SHA-256, the printing's record, its set edition, local set and
  localization, the share row (short link, corners, carousel), every module of the checkout the exporter
  loads (`gallery_prepare.py` for the cover included) and Pillow's version. A change to
  another printing rebuilds nothing; a change to this one, or a pulled fix to the cover (#691),
  rebuilds it once it is opened. The inbox asks for the fingerprint again only after the catalogue
  files or the code changed.
- **No unseen approval.** An order names the draft version the owner saw; a draft that changed since
  is refused with 409. An order keeps the images, caption and alt texts it froze.

Keep the photo checkout current (`git pull`), like the catalogue. A carousel shows every image in
order, each with its own alt text.

**Posting (#646, owner decisions 2026-11-24).** With `--uploader` pointing at the owner's upload
service and its key in the environment variable `UPLOADER_KEY` (never in a file, the repository
or a log), each draft offers the SnoreDex accounts on Instagram, Facebook and Threads, all
preselected, and a time; the uploader's other accounts never appear and cannot be posted to (owner decision
2026-11-25). The list shows at once; an opened draft's send form follows when the uploader names the accounts. Only the owner's
click, after a confirmation, posts: "Jetzt posten" at once, "Einplanen" at the chosen time. The
order freezes the draft the owner saw in `.posts/<SPEC>/` inside the data folder, so a later catalogue
change never alters it; a draft that changed since the page loaded is refused. A queue thread sends
every due order: it uploads the images to the uploader, which serves them to Meta under an
unguessable URL, and starts one job per account. Orders live on disk, so a scheduled post survives a
restart. Every job carries a `clientRef` the uploader deduplicates on, so a restart between sending
and recording never posts twice. The page shows each account's state and permalink; a job that failed
before publishing shows its reason and can be sent again, as a new attempt. A planned order can be
taken back until it goes; a sent post cannot. One order per draft. The queue touches only accounts
still to send or still running: a published or failed one costs no call to the uploader and no write,
and an order is written only when one of its accounts changed. An `order.json` that cannot be read is
logged under its SPEC and shown at its own post; the other orders go on (#676).

**Permalinks into the data (#646).** With the intake runner enabled, its worker checks published
orders after each intake run and otherwise once a minute. It gathers their links by printing and
platform (`instagramPosts`, `facebookPosts`, `threadsPosts`), freezes a batch in
`.work/permalinks/intake-run.json`, and imports it in the runner's own checkout. The mounted
catalogue checkout stays read-only. It validates the complete result before replacing `social.json`,
runs `regen.py`, commits, audits the commit, and opens or reuses a data PR through the same branch
and exact-head required-check guards as intake. A failed or still-running target contributes no link;
a broken order is logged under its SPEC and the others go on. Repeated links are added only once.

A restart or lost response resumes the saved batch and its PR. Targets published meanwhile join the
next batch. Once the unchanged batch is on main, subsequent checks make no Git/API call or write.
Errors and the PR number/head remain beside the batch; a failure is retried on the next worker turn.
This starts neither a post nor a Pages run. `sync` brings merged links into the inbox; their public
display is checked after the next authorized Pages deployment, against the printing, platform,
permalink, short-link target and preview. The phone/test-account acceptance in #646 remains separate.

Without a runner, the existing local import from the data folder or its read-only share is available
for an authorized data PR (AGENTS.md):

```console
python verification/photo_inbox/permalinks.py I:\
```

A JPEG is decoded completely. A DNG is checked at header level only (a TIFF whose first IFD carries
`DNGVersion`); the intake derives the cleaned public copy from it. Intake takes the described jobs.

| Request | Does |
|---|---|
| `POST /uploads` | one photo as `application/octet-stream`; 201 new, 200 already there |
| `GET /jobs` | every job, newest first |
| `GET /runs` | every intake run the jobs record, newest first, and the last nightly round (#685) |
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
| `GET /posts` | every shared printing, with its draft where it is built already and its order; it builds nothing (needs `--repo` and `--photos`) |
| `GET /posts/<SPEC>` | that printing's draft, built now unless it is built for its current inputs (#678) |
| `GET /posts/<SPEC>/image?n=1` | that draft's post image, `n` counting the carousel |
| `GET /accounts` | the uploader's SnoreDex accounts on Instagram, Facebook and Threads (needs `--uploader`) |
| `POST /posts/<SPEC>/order` | JSON `{"draft", "accounts", "at"}`: posts now (`at` null) or at that time; 409 for a changed draft or a second order |
| `DELETE /posts/<SPEC>/order` | takes back a planned order; 409 once it was sent |
| `POST /posts/<SPEC>/retry` | JSON `{"account"}`: sends a failed job again |

## Run

```console
pip install -r verification/photo_inbox/requirements.lock
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
  - **Fixed tools** (#681, owner decision D04): the base image is named by its digest, and
    `requirements.lock` pins every Python package, dependencies included; `requirements.txt` keeps the
    ranges the lock is chosen from. `toolchain.json` records the rest of the accepted state: the
    Python version of that base, Tesseract's version and the languages. Debian's packages, Tesseract
    among them, follow bookworm's updates and are not pinned.
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
the owner or Hermes runs, never an agent (AGENTS.md). Hermes follows the skill
[`snoredex-inbox-update`](../../.agents/skills/snoredex-inbox-update/SKILL.md) when the owner says
"Update": it checks that no intake run is going, updates, checks the version line and reports. For
it, run `sh update.sh` in that folder
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
- **Werkzeuge:** `Werkzeuge wie abgenommen` when Python, every locked package, Tesseract and its
  languages are the accepted ones; else `Werkzeuge weichen ab`, with the differences under `tools` in
  `/version`. In the container, `docker compose exec inbox python verification/photo_inbox/toolchain.py`
  prints them.

**Rollback** is the owner's decision. Building an earlier accepted commit restores its tools: the
same base by digest and the same locked packages. Only a Debian package can have moved since, and the
version line shows it. A renewed lock or base is its own change, with the inbox suites and the
image's smoke test, never a side effect.

The workflow `Inbox image` builds the image on every pull request that touches the inbox. It checks
Tesseract's languages, that the image has the accepted tools (`toolchain.py --check`) and the number
guard's tests, starts the inbox against the repository and runs `docker/smoke.py` inside it. The smoke
test covers the page, the catalogue, suggested corners, a printed number read, and a version line
naming the commit just built with the accepted tools.

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
python verification/photo_inbox/intake.py I:\<job> --photos <photo checkout> [--pr] [--result <file>]
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
- Preview and gallery images come from the approved corners, with the gallery workflow's own encoder
  (`gallery_prepare.webp_renditions` and `png_preview`, #680): WebP at 240, 480 and up to 1200 px and a
  360 px PNG preview carrying the source's ICC profile, so the same face gives the same bytes on both
  paths. They replace the item's image unless that already is an owner photograph, which the item
  keeps. A new share row records the corners as `postCorners`. A photo of a printing that keeps its
  owner photograph is a further piece of evidence only (owner decision D03, #675): exactly one SPEC, no
  share row, no short link. It becomes a carousel candidate only when the owner picks it (#646).
- Then `regen.py --photos`, which checks the model once together with the photo archive's originals
  (#677), and a commit on `intake/SPEC-nnnn`. `--pr` pushes it and opens the pull request, which is
  merged on green CI (AGENTS.md). `--dry-run` writes nothing.
- It prints the branch. `--result` also writes what was filed as JSON: `branch`, `specimen`, `itemId`
  and `keeps`, the owner photo's SPEC the printing keeps, or `null`.

## Intake run on the Homelab (#659)

`runner.py` runs the whole chain in the inbox container, without an agent. It starts from the
**Übernehmen** button on a job, or each night at 03:00 UTC for every job that is ready, failed runs
included. A job is ready when it has its printing, approved corners and no unconfirmed number mismatch,
and is not filed yet.

1. `intake.py` files the job in the run's own clones (`.work/` in the data folder) and hands its result
   over with `--result`. The run then pushes the branch and opens its pull request.
2. The pull request is merged at the head the run pushed, once every check main's ruleset requires
   (`gate (ubuntu-latest)`, `gate (windows-latest)`) passed there (#674). Another green check never
   stands in for a required one. A red check, a head someone else moved, or a main that requires no
   check stops the run with its link.
3. `Publish site` runs on main, when the filing changed a file the Pages artifact carries
   (`scripts/publish.py`); otherwise nothing is deployed (#675).
4. `Provision Snoredex short links` runs for the printing; its verified alias is read from the run's
   artifact.
5. A second pull request records the alias in `data/social.json` and is merged on green CI. Once `sync`
   has pulled main, the Posts tab shows the draft.

A further piece of evidence (`keeps` in the result) ends after step 3: no short link, no second pull
request, and the printing's image and share row stay as they are.

**Läufe (#685).** The tab lists every run from the jobs' `intake-run.json`, newest first, in three groups:
waiting or running, failed, done. Each run shows a thumbnail that jumps to its photo, its SPEC and
printing, where it came from (the button or the nightly round), its start and end, the step it is at or
stopped at and the steps done, and links to its intake PR, its alias PR and its short link. A failed one
shows the error the run stored and "Erneut versuchen", the same `POST /jobs/<id>/intake` as on the
photo. Above them stands the last nightly round with the number of jobs it started; without a runner
the tab says so. It reads only; the run records `origin`, `queuedAt`, `startedAt` and `finishedAt` for
it, the night `.work/nightly.json`. Approvals, pushed commits and request tokens stay off the page.

The job shows each step, and when a step fails, the reason. The run writes every finished step to
`intake-run.json` beside the job, so a new start, by the button or the night, carries on where it
stopped:

- `intake.py` finds its archive copy again by its bytes.
- An open pull request is reused, and a merged one gets no new action.
- The branch on GitHub is reused when it holds the same files, and replaced only when it holds a commit
  this run pushed, with a lease on exactly that commit. Anything else on it is someone's: it stays, and
  the run stops (#674). The run checks the head itself and does not rely on native auto-merge.
- An alias already on main is not recorded again.
- `Publish site` and `Provision Snoredex short links` are dispatched once and followed by the id of the
  run GitHub started (#673), never by its start time, so a foreign run of the same workflow decides
  nothing. The id is written beside the job: a new start waits for that same run.
- The dispatch is written down before GitHub hears of it, with a request token the run carries in its
  title (`run-name`). An answer lost on the way is found again by that token. A new dispatch follows
  only a run that clearly failed, or once GitHub lists every run since the dispatch, ten minutes on,
  and none carries the token. Until then the job says it is unresolved.

A restart of the container marks a cut-off run as interrupted.

An approval holds for exactly one printing (owner decision D01, 2026-11-25, #672). Queuing, by the
button or the night, freezes the photo's hash, its printing and its corners in `intake-run.json`:

- Intake starts only when the job still has the frozen printing and corners; otherwise the run stops
  before anything is filed.
- Before the short link and again before the alias pull request, the run checks on main that its SPEC
  is filed for the frozen printing. A different or no unique printing stops the run there.
- A run from before the freeze takes the printing main filed its SPEC for.
- The run records which printing a short link was verified for. The alias pull request verifies the
  link again when that printing is unknown or another one, so a row never gets another printing's link.
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
pip install -r requirements.txt -r verification/photo_inbox/requirements.lock
python verification/photo_inbox/test_app.py
python verification/photo_inbox/test_intake.py --photos <photo checkout>
python verification/photo_inbox/test_number_check.py
python verification/photo_inbox/test_runner.py
python verification/test_instagram_package.py
```

CI runs them on every pull request that changes the inbox, `scripts/`, a Python file in
`verification/` or the requirements (`inbox-image.yml`, #677): the image job runs the number guard,
the intake run and the smoke test in the built image, and the `inbox suites` job runs `test_app.py`,
`test_intake.py` on synthetic photos and `test_instagram_package.py`. A pull request that changes only
Markdown starts neither; `verification/test_inbox_ci.py` checks that filter. The byte comparison with
the photo archive stays a local run: `test_intake.py --photos <photo checkout>`.

What each suite covers:

- `test_runner.py`: the intake run against local Git remotes and a stand-in GitHub. The whole chain;
  a restart after any step without a second filing, pull request or merge; red CI and a refused job;
  the frozen approval (#672); the workflow runs followed by their id (#673); a foreign commit on the
  branch, the required checks at the pushed head and a PR merged by hand (#674); a further piece of
  evidence (#675); the run records and the nightly round (#685); the page's button and lock.
- `test_intake.py`: a synthetic phone photo (sideways, with GPS) filed for a printing with and one
  without an owner photo, every `check.py` rule on the result, the refusals, an orphaned archive
  copy, two intakes racing for a number, the single gate run with the archive (#677) and one encoder
  for intake and gallery (#680); with the photo archive, SPEC-1125's gallery and preview files byte
  for byte.
- `test_number_check.py`: the misreadings seen in #655 as verdicts, and when the guard stops intake.
- `test_app.py`: uploads (JPEG with GPS kept privately, DNGs in both byte orders, refused files,
  limits, repeats), the dashboard, the trash, the overview for every stage, restart, the card corners
  and the number read (with Tesseract installed, else it says so), the Posts tab with a stand-in
  exporter (a draft built when opened, once per fingerprint, a stale draft refused; #678) and a
  stand-in uploader (orders, retries, deduplication, finished targets left alone, a broken order
  isolated; #676), the Läufe tab (#685), the version line with its tools (#681), the archive copy,
  and in a phone-sized Chromium the tabs, labels in a wide font and no sideways scroll. It is not
  part of `regen.py`, whose gate stays standard-library only.

## Still open

- The Instagram package from an owner SPEC and its acceptance with the pilot cards: #625.
- HEIC input, an edited JPEG and its DNG in one job, and questions on the job: #660.

[Upload and import issue](https://github.com/m4s-ai/snoredex-data/issues/626) · [Bulk upload and dashboard](https://github.com/m4s-ai/snoredex-data/issues/639)
