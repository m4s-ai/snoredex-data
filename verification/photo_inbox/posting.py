"""Post an approved draft through the owner's uploader, now or at a chosen time (#646).

Only the owner's click creates an order. An order freezes the draft the owner saw (images, caption,
alt texts) beside it in the private data folder, so a later catalogue change never alters what goes
out. Each target account gets one uploader job; a target that failed before publishing can be sent
again on request, under a new attempt. Every request carries a `clientRef` the uploader deduplicates
on, so a restart between sending and recording a job never posts twice. Orders live on disk, so a
scheduled post survives a restart of the service.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

POSTS = ".posts"
ACTIVE = ("queued", "container_created", "processing", "publishing")
PLATFORMS = {"ig": "instagramPosts", "fb_page": "facebookPosts", "threads": "threadsPosts"}
SLIDE = re.compile(r"post(?:-([0-9]+))?\.jpg")


class UploaderError(Exception):
    pass


class Uploader:
    """The owner's upload service; the API key comes from the environment, never from a file here."""

    def __init__(self, base, key, timeout=60):
        self.base, self.key, self.timeout = base.rstrip("/"), key, timeout

    def call(self, method, path, body=None, content_type="application/json"):
        data = body if isinstance(body, bytes) or body is None else json.dumps(body).encode()
        request = Request(self.base + path, data=data, method=method,
                          headers={"Authorization": f"Bearer {self.key}", "Content-Type": content_type})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except HTTPError as error:
            try:
                message = json.loads(error.read()).get("error")
            except ValueError:
                message = None
            raise UploaderError(message or f"Uploader antwortet {error.code}") from error
        except (URLError, OSError, ValueError) as error:
            raise UploaderError(f"Uploader nicht erreichbar: {error}") from error

    def accounts(self):
        return self.call("GET", "/api/v1/accounts")["accounts"]

    def media(self, jpeg):
        return self.call("POST", "/api/v1/media", jpeg, "image/jpeg")["media"]["url"]

    def upload(self, body):
        return self.call("POST", "/api/v1/upload", body)["job"]

    def job(self, job_id):
        return self.call("GET", f"/api/v1/jobs/{job_id}")["job"]


def write_json(path, data):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def slides(folder):
    """The draft's images in carousel order: post.jpg, then post-2.jpg, post-3.jpg, ..."""
    numbered = [(int(match[1] or 1), path.name) for path in folder.iterdir() if (match := SLIDE.fullmatch(path.name))]
    return [name for _, name in sorted(numbered)]


def alt_name(image):
    return image.replace("post", "alt-text").replace(".jpg", ".txt")


def order_folder(root, specimen):
    if not re.fullmatch(r"SPEC-[0-9]{4,8}", str(specimen)):
        raise LookupError(specimen)
    return root / POSTS / specimen


def read_order(root, specimen):
    path = order_folder(root, specimen) / "order.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def due_time(value):
    if not value:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Gib Datum und Uhrzeit für den Post an.") from error
    if moment.tzinfo is None:
        raise ValueError("Die Uhrzeit braucht eine Zeitzone.")
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def place_order(root, specimen, row, draft, accounts, known, at=None):
    """Freeze the draft the owner approved and queue it for the chosen accounts."""
    folder = order_folder(root, specimen)
    if folder.exists():
        raise PermissionError("Für diesen Entwurf gibt es schon einen Auftrag.")
    chosen = list(dict.fromkeys(accounts or []))
    if not chosen or any(account not in known for account in chosen):
        raise ValueError("Wähle mindestens ein verbundenes Konto.")
    images = slides(draft)
    order = {"specimen": specimen, "itemId": row["itemId"], "draft": draft.name, "id": secrets.token_hex(6),
             "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "dueAt": due_time(at),
             "caption": (draft / "caption-draft.txt").read_text(encoding="utf-8").strip(),
             "images": [{"file": name, "alt": (draft / alt_name(name)).read_text(encoding="utf-8").strip()}
                        for name in images],
             "targets": {account: {"attempt": 1, "status": "pending"} for account in chosen}}
    staged = folder.with_name(".staged-" + folder.name)  # the queue reads SPEC-* folders only
    shutil.rmtree(staged, ignore_errors=True)
    staged.mkdir(parents=True)
    for name in images:
        shutil.copyfile(draft / name, staged / name)
    write_json(staged / "order.json", order)
    staged.rename(folder)
    return order


def cancel_order(root, specimen):
    order = read_order(root, specimen)
    if order is None:
        raise LookupError
    # a send that was started may have reached the uploader, even if the inbox never heard back or
    # stopped on the way: only a plan that was never tried goes back
    if any(target.get("tried") or target["status"] != "pending" for target in order["targets"].values()):
        raise PermissionError("Der Post ist schon unterwegs und lässt sich nicht mehr zurücknehmen.")
    shutil.rmtree(order_folder(root, specimen))


def retry_target(root, specimen, account):
    order = read_order(root, specimen)
    target = (order or {}).get("targets", {}).get(account)
    if target is None:
        raise LookupError
    if target["status"] != "failed":
        raise PermissionError("Nur ein gescheiterter Auftrag lässt sich erneut senden.")
    order["targets"][account] = {"attempt": target["attempt"] + 1, "status": "pending"}
    write_json(order_folder(root, specimen) / "order.json", order)
    return order


def media_urls(order, folder, uploader, cache):
    """The images under public URLs Meta can fetch, uploaded once per round: the uploader drops an
    image an hour after upload unless a running job uses it, so a later retry uploads it again."""
    if "urls" not in cache:
        cache["urls"] = [uploader.media((folder / image["file"]).read_bytes()) for image in order["images"]]
    return cache["urls"]


def request_body(order, account, urls):
    target = order["targets"][account]
    body = {"accountId": account, "caption": order["caption"],
            "clientRef": f"snoredex:{order['specimen']}:{order['id']}:{account}:{target['attempt']}"}
    if len(urls) == 1:
        return dict(body, imageUrl=urls[0], altText=order["images"][0]["alt"])
    return dict(body, images=[{"imageUrl": url, "altText": image["alt"]} for url, image in zip(urls, order["images"])])


def advance(order, folder, uploader, account, cache):
    """One step for one target: send it once, then follow its job until it is published or failed."""
    target = order["targets"][account]
    if target["status"] == "pending":
        job = uploader.upload(request_body(order, account, media_urls(order, folder, uploader, cache)))
    elif target["status"] in ACTIVE:
        job = uploader.job(target["jobId"])
    else:
        return
    target.update(jobId=job["id"], status=job["status"], permalink=job.get("permalink"), error=job.get("error"))
    target.pop("problem", None)


def tick(root, uploader, now=None):
    """Send every due order and follow its jobs; a failure to reach the uploader is retried next time."""
    moment = now or datetime.now(timezone.utc)
    for path in sorted((root / POSTS).glob("SPEC-*/order.json")):
        order = json.loads(path.read_text(encoding="utf-8"))
        if datetime.fromisoformat(order["dueAt"]) > moment:
            continue
        cache = {}
        for account, target in order["targets"].items():
            if target["status"] == "pending" and not target.get("tried"):
                target["tried"] = True  # recorded before the uploader is called, so a crash cannot hide it
                write_json(path, order)
            try:
                advance(order, path.parent, uploader, account, cache)
            except UploaderError as error:
                order["targets"][account]["problem"] = str(error)
            write_json(path, order)


def run_scheduler(root, uploader, lock, every=20):
    def loop():
        while True:
            with lock:
                try:
                    tick(root, uploader)
                except (OSError, ValueError, KeyError) as error:  # one broken order must not stop the queue
                    print(f"Post-Warteschlange: {error}", flush=True)
            time.sleep(every)

    threading.Thread(target=loop, name="post-queue", daemon=True).start()


def order_view(order):
    """What the page shows of an order: never the media URLs."""
    if order is None:
        return None
    return {"dueAt": order["dueAt"], "createdAt": order["createdAt"],
            "targets": {account: {key: target.get(key) for key in ("status", "permalink", "error", "problem",
                                                                    "attempt", "tried")}
                        for account, target in order["targets"].items()}}


def published_links(root):
    """Every permalink a published order reports, by item and data field, for the data PR."""
    links = {}
    for path in sorted(Path(root, POSTS).glob("SPEC-*/order.json")):
        order = json.loads(path.read_text(encoding="utf-8"))
        for account, target in order["targets"].items():
            field = PLATFORMS.get(account.split(":", 1)[0])
            if field and target["status"] == "published" and target.get("permalink"):
                links.setdefault(order["itemId"], {}).setdefault(field, []).append(target["permalink"])
    return links
