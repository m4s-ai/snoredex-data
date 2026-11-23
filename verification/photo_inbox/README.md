<!-- doc: role=private photo inbox for owner phone uploads (#626); stage=task -->

# Private SnoreDex photo inbox (#626)

A small LAN service where the owner hands in an own photo from the phone: the iPhone's DNG
(ProRAW) or a JPEG. It keeps the original bytes unchanged, GPS included, in a private folder outside
every Git checkout and publishes nothing. Each upload becomes a job folder named by the SHA-256 of
its bytes, holding `photo.dng` or `photo.jpg` and `job.json` with the SPEC hint or note, `ownPhoto`,
the file name and the hash. The same photo with the same details is the same job (a double tap or a
repeat after a restart); the same photo with other details is refused with 409.

The German mobile page (`templates/index.html`, `static/`) asks for the photo (camera, gallery or
files), the SPEC number or a short note and the confirmation "selbst aufgenommen". It shows the job
number, a repeat and each refusal in words. There is no access code (owner decision, 2026-11-23):
the service is reachable only in the home network.

A JPEG is decoded completely. A DNG is checked at header level only (a TIFF whose first IFD carries
`DNGVersion`); the raw decoder at intake proves its pixels, and the intake derives the cleaned public
copy from it.

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

It covers a JPEG with GPS (kept privately, byte for byte), DNGs in both byte orders, a plain TIFF and
a truncated DNG header, a missing owner confirmation or card hint, invalid SPEC numbers and notes,
non-photo and truncated JPEG files, the size and pixel limits, repeat and conflicting uploads, a
restart, an inbox inside a Git checkout, the page in a phone-sized Chromium, and the archive copy of
a phone-like DNG and JPEG (location, maker, XMP and second frame gone; pixels, profile and
orientation kept; a DNG without preview refused). It is not part of `regen.py`, whose gate stays
standard-library only.

## Still open

1. Done 2026-11-23: an iPhone 15 Pro ProRAW DNG (DNG 1.6, 12 megapixels) arrived unchanged from
   the phone's photo picker and is readable over the share, hash matching its job.
2. Done 2026-11-23: the first job went through intake as SPEC-1111; `derive.py` now makes that
   archive copy. Next: its Instagram package through #625.
3. Later in #626: HEIC input, an edited JPEG and its DNG in one job, status and questions on the job,
   and resuming after an interrupted archive push.

[Upload and import issue](https://github.com/m4s-ai/snoredex-data/issues/626)
