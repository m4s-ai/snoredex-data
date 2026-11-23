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

## Check

```console
pip install -r requirements.txt -r verification/photo_inbox/requirements.txt
python verification/photo_inbox/test_app.py
```

It covers a JPEG with GPS (kept privately, byte for byte), DNGs in both byte orders, a plain TIFF and
a truncated DNG header, a missing owner confirmation or card hint, invalid SPEC numbers and notes,
non-photo and truncated JPEG files, the size and pixel limits, repeat and conflicting uploads, a
restart, an inbox inside a Git checkout, and the page in a phone-sized Chromium. It is not part of
`regen.py`, whose gate stays standard-library only.

## Still open

1. Run it on the Homelab and upload a DNG from the iPhone in the home network; note the address,
   runtime and persistent folder, and where the local import reads the jobs.
2. Hand a job's photo to intake: the cleaned, checked copy goes through #625; raw bytes never leave
   the inbox.
3. Later in #626: HEIC input, an edited JPEG and its DNG in one job, status and questions on the job,
   and resuming after an interrupted archive push.

[Upload and import issue](https://github.com/m4s-ai/snoredex-data/issues/626)
