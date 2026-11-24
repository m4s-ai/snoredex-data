<!-- doc: role=private photo inbox for owner phone uploads (#626, #639, #641); stage=task -->

# Private SnoreDex photo inbox (#626, #639, #641)

A small LAN service where the owner hands in their own photos from the phone: the iPhone's DNG
(ProRAW) or JPEG. Every photo here is the owner's own; images found elsewhere go through the regular
specimen intake, never through this inbox. The service keeps the original bytes unchanged, GPS
included, in a private folder outside every Git checkout and publishes nothing. Each photo becomes a
job folder named by the SHA-256 of its bytes, holding `photo.dng` or `photo.jpg` and `job.json` with
`ownPhoto`, the file name, the hash, `receivedAt`, and once described `specimenHint`, `note` and
`describedAt`. A job is its bytes: uploading the same photo again, described or not, is the same job.

Upload and card assignment are separate (owner decision, 2026-11-23). The German mobile page
(`templates/index.html`, `static/`) takes any number of photos at once, without details, and sends
them one by one with progress and a result per file; a bad file does not stop the rest. Below it, a
dashboard lists every job, newest first, with a preview (a DNG shows its embedded full-size
preview), a link to a large view, its state ("ohne Angabe", "beschrieben" or "übernommen als
SPEC-nnnn") and a form for the SPEC number, a short note or the exact printing picked from the
catalogue (`itemId`), checked as the single upload always checked them. A printing is picked by
its label, which names everything that tells variants apart (foil pattern, markings, a size other
than standard) and carries the `itemId` where two printings would still read the same. Its views show all jobs,
those without details, the unclassified ones (no printing yet) and those already filed. Saving writes `job.json`
at once; a description can be corrected, the photo never changes. Previews are cached beside the job
as `preview-400.jpg` and `preview-1600.jpg`, upright and without Exif. There is no access code (owner
decision, 2026-11-23): the service is reachable only in the home network.

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
beside the job as `archive.sha256`; a failed derivation is not cached and is tried again. Views show the printings with an owner photo, those without and every
printing, with a stage filter, a search, the count per stage and statistics by language or set, all
counted from the same rows. The published catalogue is re-read every ten minutes; when the site
cannot be read, nothing counts as online and the page says so. The overview writes nothing to the
repository, the photo archive or the site. Keep the checkout current (`git pull` on `main`).

A JPEG is decoded completely. A DNG is checked at header level only (a TIFF whose first IFD carries
`DNGVersion`); the intake derives the cleaned public copy from it. Intake takes the described jobs.

| Request | Does |
|---|---|
| `POST /uploads` | one photo as `application/octet-stream`; 201 new, 200 already there |
| `GET /jobs` | every job, newest first |
| `GET /jobs/<id>/preview?size=400\|1600` | the cached preview JPEG |
| `POST /jobs/<id>` | JSON `{"specimen", "note", "itemId"}`: saves the description |
| `DELETE /jobs/<id>` | moves an unfiled job to the trash; 409 when filed or without catalogue |
| `GET /trash` | the trashed jobs; anything older than 30 days is deleted first |
| `GET /trash/<id>/preview?size=400\|1600` | the preview of a trashed job |
| `POST /trash/<id>/restore` | puts a trashed job back |
| `DELETE /trash/<id>` | deletes a trashed job for good; 409 when filed or without catalogue |
| `GET /overview` | every active printing with its stage, links and jobs (needs `--repo`) |

## Run

```console
pip install -r verification/photo_inbox/requirements.txt
python verification/photo_inbox/app.py --data-dir <private folder outside Git> --host 0.0.0.0 --repo <checkout of main>
```

Without `--host` the service listens on loopback only; `--host 0.0.0.0` (or a reverse proxy on the
Homelab) makes it reachable in the home network on port 8765 (`--port`). Uploads are limited to
200 MB, and JPEGs to 60 megapixels.

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

## Check

```console
pip install -r requirements.txt -r verification/photo_inbox/requirements.txt
python verification/photo_inbox/test_app.py
```

It covers uploads without details (a JPEG with GPS kept privately, byte for byte; DNGs in both byte
orders; a plain TIFF, a truncated DNG header, non-photo and truncated JPEG files refused; the size
and pixel limits; repeats), the dashboard (newest first, previews without Exif or GPS, a DNG without
an embedded preview, invalid and corrected descriptions, a described photo uploaded again), the
trash (no delete without catalogue or of a filed job, restore, a re-upload, delete for good, emptied
after 30 days), the overview with test data for every stage (an unreadable site counts nothing as
online), a restart, an inbox inside a Git checkout, and in a phone-sized Chromium a bulk upload with
one bad file, a description with its printing, the views, counts and statistics, and delete,
restore and delete for good, and the archive copy of a phone-like DNG and JPEG (location, maker, XMP and
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
