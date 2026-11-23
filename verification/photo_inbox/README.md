<!-- doc: role=private photo inbox for owner phone uploads (#626); stage=task -->

# Private SnoreDex photo inbox (#626)

A small LAN service where the owner hands in an own JPEG from the phone. It keeps the original bytes
unchanged, GPS included, in a private folder outside every Git checkout and publishes nothing. Each
upload becomes a job folder named by the SHA-256 of its bytes, holding `photo.jpg` and `job.json`
with the SPEC hint or note, `ownPhoto` and the hash. The same photo with the same details is the same
job (a double tap or a repeat after a restart); the same photo with other details is refused with 409.

The German mobile page (`templates/index.html`, `static/`) asks for the photo (camera or gallery),
the SPEC number or a short note, the confirmation "selbst aufgenommen" and the upload code. It shows
the job number, a repeat and each refusal in words. The code travels only in the request's bearer
header, never in a URL, and stays on the phone after the first accepted upload.

## Run

```console
pip install -r verification/photo_inbox/requirements.txt
python verification/photo_inbox/app.py --data-dir <private folder outside Git>
```

Set `SNOREDEX_INBOX_TOKEN` (16-128 letters, digits, `-` or `_`) in the service environment, and give
the code to the owner privately. The default address is loopback only; `--host` and `--port`, or a
reverse proxy on the Homelab, make it reachable in the home network. Uploads are limited to 24 MB
and 60 megapixels.

## Check

```console
pip install -r requirements.txt -r verification/photo_inbox/requirements.txt
python verification/photo_inbox/test_app.py
```

It covers a JPEG with GPS (kept privately, byte for byte), a wrong or missing code, a missing owner
confirmation or card hint, invalid SPEC numbers and notes, non-JPEG and truncated files, the size and
pixel limits, repeat and conflicting uploads, a restart, an inbox inside a Git checkout, and the page
in a phone-sized Chromium. It is not part of `regen.py`, whose gate stays standard-library only.

## Still open

1. Run it on the Homelab and upload from the real phone in the home network; note the address,
   runtime and persistent folder, and where the local import reads the jobs.
2. Hand a job's photo to intake: the cleaned, checked copy goes through #625; raw bytes never leave
   the inbox.
3. Later in #626: an optional DNG per job, HEIC input, status and questions on the job, and
   resuming after an interrupted archive push.

[Upload and import issue](https://github.com/m4s-ai/snoredex-data/issues/626) · [Instagram export PR](https://github.com/m4s-ai/snoredex-data/pull/630)
