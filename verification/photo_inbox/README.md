<!-- doc: role=private photo inbox for owner phone uploads (#626, #639); stage=task -->

# Private SnoreDex photo inbox (#626, #639)

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
preview), a link to a large view, its state ("ohne Angabe" or "beschrieben") and a form for the SPEC
number or a short note, checked as the single upload always checked them. Saving writes `job.json`
at once; a description can be corrected, the photo never changes. Previews are cached beside the job
as `preview-400.jpg` and `preview-1600.jpg`, upright and without Exif. There is no access code (owner
decision, 2026-11-23): the service is reachable only in the home network.

A JPEG is decoded completely. A DNG is checked at header level only (a TIFF whose first IFD carries
`DNGVersion`); the intake derives the cleaned public copy from it. Intake takes the described jobs.

| Request | Does |
|---|---|
| `POST /uploads` | one photo as `application/octet-stream`; 201 new, 200 already there |
| `GET /jobs` | every job, newest first |
| `GET /jobs/<id>/preview?size=400\|1600` | the cached preview JPEG |
| `POST /jobs/<id>` | JSON `{"specimen", "note"}`: saves the description |

## Run

```console
pip install -r verification/photo_inbox/requirements.txt
python verification/photo_inbox/app.py --data-dir <private folder outside Git> --host 0.0.0.0
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
an embedded preview, invalid and corrected descriptions, a described photo uploaded again), a
restart, an inbox inside a Git checkout, a bulk upload with one bad file and a description saved in a
phone-sized Chromium, and the archive copy of a phone-like DNG and JPEG (location, maker, XMP and
second frame gone; pixels, profile and orientation kept; a DNG without preview refused). It is not
part of `regen.py`, whose gate stays standard-library only.

## Still open

1. Done 2026-11-23: an iPhone 15 Pro ProRAW DNG (DNG 1.6, 12 megapixels) arrived unchanged from
   the phone's photo picker and is readable over the share, hash matching its job.
2. Done 2026-11-23: the first job went through intake as SPEC-1111; `derive.py` now makes that
   archive copy. Next: its Instagram package through #625.
3. Done in #639: bulk upload and the dashboard. Open there: showing "filed as SPEC-nnnn" on a job,
   since intake reads the share without writing to it.
4. Later in #626: HEIC input, an edited JPEG and its DNG in one job, questions on the job, and
   resuming after an interrupted archive push.

[Upload and import issue](https://github.com/m4s-ai/snoredex-data/issues/626) · [Bulk upload and dashboard](https://github.com/m4s-ai/snoredex-data/issues/639)
