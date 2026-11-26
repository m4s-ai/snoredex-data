"""Smoke test of a running inbox container: page, catalogue, a photo with its suggested corners and
Tesseract reading a printed number. Runs inside the container, where Pillow and Tesseract are:

    docker exec <container> python verification/photo_inbox/docker/smoke.py http://127.0.0.1:8765
"""

from io import BytesIO
import json
import os
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import number_check  # noqa: E402

CARD = [[300, 400], [1380, 410], [1370, 1910], [310, 1900]]


def call(base, path, data=None, content_type="application/json"):
    request = Request(base + path, data=data, method="POST" if data is not None else "GET",
                      headers={"Content-Type": content_type})
    with urlopen(request, timeout=120) as response:
        body = response.read()
        return response.status, body


def card_photo():
    photo = Image.new("RGB", (1700, 2300), (20, 20, 24))
    draw = ImageDraw.Draw(photo)
    draw.polygon([tuple(p) for p in CARD], fill=(225, 205, 60))
    draw.text((1080, 1800), "1/64", fill=(10, 10, 10), font=ImageFont.load_default(size=56))
    return photo


def main(base):
    for _ in range(60):
        try:
            if call(base, "/")[0] == 200:
                break
        except OSError:
            time.sleep(1)
    else:
        raise SystemExit("the inbox did not answer")
    status, body = call(base, "/overview")
    assert status == 200 and json.loads(body)["rows"], "the overview reads the mounted catalogue"
    out = BytesIO()
    card_photo().save(out, "JPEG", quality=92)
    status, body = call(base, "/uploads", out.getvalue(), "application/octet-stream")
    job = json.loads(body)["id"]
    status, body = call(base, f"/jobs/{job}/corners")
    assert status == 200 and json.loads(body)["candidates"], "OpenCV suggests the card's corners"
    face = card_photo().crop((300, 400, 1380, 1910))
    found = number_check.check(face, "1", "64", "Japanese")
    assert found["result"] == "match", found
    # #666: the image names the commit it was built from, and the mounted checkout is that commit
    status, body = call(base, "/version")
    version = json.loads(body)
    built = os.environ.get("INBOX_COMMIT")
    assert built and version["code"]["commit"] == built and version["code"]["source"] == "image", version
    assert version["data"]["commit"] == built and version["codeChanged"] is False, version
    assert version["tools"] == {"matches": True, "drift": []}, version["tools"]  # #681: the accepted tools
    print("inbox container: page, catalogue, corners, Tesseract, tools and version line work")


if __name__ == "__main__":
    main(sys.argv[1].rstrip("/"))
