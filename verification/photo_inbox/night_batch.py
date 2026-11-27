"""D05/D06 (#679): one nightly deployment, durable alias groups, one alias PR and deferred public checks."""
from io import BytesIO
import json
import re
import subprocess
from uuid import uuid4
import zipfile

import runner
from card_pages import PLATFORM_URLS, read_social
from yourls_cards import ASSET_BASE_URL, SHORT_BASE, card_plan, request, select_keyword, verify_public_page, verify_redirect


def folder(run, batch):
    if not re.fullmatch(r"[0-9a-f]{32}", batch):
        raise ValueError("Invalid nightly batch id")
    return run.root / runner.WORK / "night-batches" / batch


def pending(run):
    return runner.read_state(run.root / runner.WORK / "publication").get("items", [])


def defer(run, items):
    path = run.root / runner.WORK / "publication"
    before = pending(run)
    after = sorted(set(before).union(items))
    if after != before:
        path.mkdir(parents=True, exist_ok=True)
        runner.write_state(path, {"items": after, "status": "pending"})


def reconciled(run, items, run_id):
    path = run.root / runner.WORK / "publication"
    remaining = sorted(set(pending(run)).difference(items))
    if path.exists():
        runner.write_state(path, {"items": remaining, "status": "pending" if remaining else "done",
                                  "verifiedAt": runner.now(), "verifiedItems": sorted(items), "publishRun": run_id})


def verify_publication(repo, items):
    """Read-only final reconciliation, without the protected YOURLS credential."""
    if not items:
        return
    local = read_social(repo)
    public = {row["itemId"]: row for row in json.loads(request(ASSET_BASE_URL + "data/social.json", 2 * 1024 * 1024))}
    for item in items:
        if public.get(item) != local[item]:
            raise runner.RunError(f"Der öffentliche Social-Datenstand für {item} ist noch nicht abgeglichen.")
        plan, preview = card_plan(item, None, repo)
        verify_public_page(plan, preview, repo)
        if local[item].get("shortAlias"):
            verify_redirect(plan)


def excluded(state, batch):
    return state.get("batch") == batch and state.get("batchExcluded")


def members(state):
    return [job for job in state.get("active", state["jobs"]) if job not in state.get("excluded", [])]


def enqueue(run, batch):
    path = folder(run, batch)
    state = runner.read_state(path)
    jobs = members(state)
    marker = "night:" + batch
    if state.get("status") == "done" or marker in run.waiting or any(job in run.waiting for job in jobs):
        return False
    for job in jobs:
        if not re.fullmatch(r"[0-9a-f]{64}", job):
            raise ValueError("Invalid nightly job id")
        current = runner.read_state(run.root / job)
        if not (run.root / job / "job.json").is_file() or excluded(current, batch):
            continue
        if "intake" not in current.get("done", []):
            current["approval"] = state["approvals"][job]
        current.update(status="queued", batch=batch, batchExcluded=False, origin="night", error=None,
                       queuedAt=runner.now(), startedAt=None, finishedAt=None)
        runner.write_state(run.root / job, current)
        run.waiting.add(job)
    runner.write_state(path, dict(state, status="queued"))
    run.waiting.add(marker)
    run.jobs.put(marker)
    return True


def create(run, jobs):
    batch = uuid4().hex
    path = folder(run, batch)
    path.mkdir(parents=True)
    runner.write_state(path, {"jobs": jobs, "approvals": {job: runner.approval(run.root / job) for job in jobs},
                              "status": "queued", "groups": [], "branch": "intake/night-" + batch + "-aliases"})
    return batch


def partition(run, ready):
    batches, fresh = [], []
    for job in dict.fromkeys(ready):
        state = runner.read_state(run.root / job)
        if job in run.waiting:
            continue
        if state.get("batch") and not excluded(state, state["batch"]):
            batches.append(state["batch"])
        else:
            fresh.append(job)
    return batches, fresh


def incomplete_publications(run):
    batches = []
    for path in (run.root / runner.WORK / "night-batches").glob("*/" + runner.STATE):
        state = runner.read_state(path.parent)
        if not state["jobs"] and state.get("status") != "done":
            batches.append(path.parent.name)
    return batches


def schedule(run, ready):
    batches, fresh = partition(run, ready)
    batches.extend(incomplete_publications(run))
    queued = []
    if fresh or not batches and not run.waiting and pending(run):
        batches.append(create(run, fresh))
    for batch in dict.fromkeys(batches):
        if enqueue(run, batch):
            queued.extend(runner.read_state(folder(run, batch))["jobs"])
    path = run.root / runner.WORK / runner.NIGHT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"at": runner.now(), "jobs": queued}) + "\n", encoding="utf-8", newline="\n")


def checked_results(payload, items, rows):
    results = payload if isinstance(payload, list) else [payload]
    if len(results) != len(items) or {row["itemId"] for row in results} != set(items):
        raise ValueError("Alias artifact does not match the frozen group")
    for row in results:
        if row.get("status") != "verified":
            continue
        checked_assignment(row, rows)
    return results


def checked_assignment(row, rows):
    expected = select_keyword(rows, row["itemId"], None)
    if (row.get("shortAlias") != expected or row.get("shortUrl") != SHORT_BASE + expected or
            row.get("targetUrl") != ASSET_BASE_URL + "cards/" + row["itemId"] + "/" or
            row.get("redirectStatus") not in (301, 302, 303, 307, 308)):
        raise ValueError("Alias artifact has a different assignment or no verified redirect")


class Batch:
    def __init__(self, run, batch):
        self.runner, self.batch, self.folder = run, batch, folder(run, batch)
        self.state = runner.read_state(self.folder)

    def save(self):
        runner.write_state(self.folder, self.state)

    def states(self):
        return [(job, runner.read_state(self.runner.root / job)) for job in self.state.get("active", [])]

    def run(self):
        self.state.update(status="running", error=None, startedAt=runner.now(), finishedAt=None)
        self.save()
        try:
            if "active" not in self.state:
                self.file()
            self.stage("publish")
            self.publish()
            self.stage("alias")
            self.aliases()
            self.stage("alias-pr")
            self.alias_pr()
            for job, state in self.states():
                runner.write_state(self.runner.root / job, dict(state, status="done", step=None,
                                   done=list(runner.STEPS), error=None, finishedAt=runner.now()))
            self.state.update(status="done", step=None, error=None, finishedAt=runner.now())
            self.save()
        except (runner.RunError, OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
            self.fail(str(error))
        finally:
            with self.runner.queue_lock:
                self.release()

    def release(self):
        for job in self.state["jobs"]:
            state = runner.read_state(self.runner.root / job)
            if not state or state.get("batch") == self.batch and not state.get("batchExcluded"):
                self.runner.waiting.discard(job)
        self.runner.waiting.discard("night:" + self.batch)

    def stage(self, name):
        self.state["step"] = name
        self.save()
        for job, state in self.states():
            runner.write_state(self.runner.root / job, dict(state, step=name, status="running", error=None,
                               startedAt=state.get("startedAt") or runner.now(), finishedAt=None))

    def file(self):
        active = []
        for job in members(self.state):
            current = runner.read_state(self.runner.root / job)
            if current.get("batch") != self.batch or excluded(current, self.batch):
                continue
            self.runner.run(job, steps=("intake", "merge"), finish=False)
            state = runner.read_state(self.runner.root / job)
            if "merge" in state.get("done", []):
                active.append(job)
            elif (self.runner.root / job).is_dir():
                with self.runner.queue_lock:
                    runner.write_state(self.runner.root / job, dict(state, batchExcluded=True))
                    self.state.setdefault("excluded", []).append(job)
                    self.save()
                    self.runner.waiting.discard(job)
        self.state["active"] = active
        self.save()

    def publish(self):
        if self.state.get("published"):
            self.publish_jobs()
            return
        self.runner.prepare()
        if "publicCheckedItems" not in self.state and self.needs_publication():
            items = set(pending(self.runner))
            items.update(self.runner.filed_printing(state) for _job, state in self.states() if not state.get("keeps"))
            self.state["publicCheckedItems"] = sorted(items)
            self.save()
        if "publicCheckedItems" in self.state:
            self.reconcile_deployment()
        self.state["published"] = True
        self.save()
        self.publish_jobs()

    def needs_publication(self):
        return bool(pending(self.runner)) or any(
            state.get("publish", True) and "publish" not in state.get("done", []) for _job, state in self.states())

    def reconcile_deployment(self):
        run = self.runner.workflow(self.folder, self.state, "pages.yml", {})
        head, items = self.runner.public_head(), self.state["publicCheckedItems"]
        repo = self.runner.data
        if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
            raise runner.RunError("Die veröffentlichte Website meldet keinen gültigen Commit.")
        self.runner.git(repo, "fetch", "-q", "origin", head)
        self.runner.git(repo, "merge-base", "--is-ancestor", run["head_sha"], head)
        self.runner.git(repo, "fetch", "-q", "origin", "main")
        self.runner.git(repo, "merge-base", "--is-ancestor", head, "FETCH_HEAD")
        self.runner.git(repo, "checkout", "-q", "--detach", head)
        deployed = read_social(repo)
        self.runner.verify_publication(items)
        self.runner.prepare()
        latest = read_social(repo)
        # A later data PR can change an already pending item while this deployment is retried.
        reconciled(self.runner, [item for item in items if deployed.get(item) == latest.get(item)], run["id"])
        self.state.update(publishRun=run["id"], publicHead=head, publicCheckedAt=runner.now())

    def publish_jobs(self):
        for job, state in self.states():
            if "publish" not in state.setdefault("done", []):
                state["done"].append("publish")
            state["publishRun"] = self.state.get("publishRun") or state.get("publishRun")
            runner.write_state(self.runner.root / job, state)

    def alias_inputs(self):
        rows, todo = read_social(self.runner.data), []
        for job, state in self.states():
            if state.get("keeps"):
                continue
            item = self.runner.filed_printing(state)
            recorded = rows[item].get("shortAlias")
            if recorded and not state.get("alias"):
                state.update(alias=recorded, aliasItem=item, aliasReused=True)
                if "alias" not in state.setdefault("done", []):
                    state["done"].append("alias")
                runner.write_state(self.runner.root / job, state)
            if not state.get("alias"):
                todo.append(item)
        return rows, todo

    def add_groups(self, todo):
        outstanding = {item for index, group in enumerate(self.state["groups"])
                       if not runner.read_state(self.folder / f"alias-{index}").get("handled") for item in group}
        todo = list(dict.fromkeys(item for item in todo if item not in outstanding))
        self.state["groups"].extend(todo[index:index + 3] for index in range(0, len(todo), 3))
        self.save()

    def aliases(self):
        self.runner.prepare()
        self.replay()
        rows, todo = self.alias_inputs()
        self.add_groups(todo)
        for index, items in enumerate(self.state["groups"]):
            if not runner.read_state(self.folder / f"alias-{index}").get("handled"):
                self.group(index, items, rows)
        if any(not state.get("alias") and not state.get("keeps") for _job, state in self.states()):
            raise runner.RunError("Ein Kurzlink fehlt noch. Bestätigte Teilerfolge bleiben gespeichert; erneut versuchen.")

    def replay(self):
        rows = read_social(self.runner.data)
        for index, items in enumerate(self.state["groups"]):
            state = runner.read_state(self.folder / f"alias-{index}")
            if state.get("handled"):
                for row in checked_results(state["outcomes"], items, rows):
                    self.apply(row, state["runId"])

    def group(self, index, items, rows):
        path = self.folder / f"alias-{index}"
        path.mkdir(exist_ok=True)
        state = runner.read_state(path)
        if not state.get("handled"):
            run = self.runner.workflow(path, state, "yourls-pilot.yml", {"item_ids": " ".join(items)}, allow_failure=True)
            artifact = self.runner.github.artifact(run["id"], "yourls-verified")
            try:
                if artifact is None:
                    raise ValueError("No alias artifact")
                with zipfile.ZipFile(BytesIO(artifact)) as archive:
                    results = checked_results(json.loads(archive.read("yourls-result.json")), items, rows)
            except (ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
                results = [{"itemId": item, "status": "failed", "error": str(error)} for item in items]
            state.update(handled=True, outcomes=results, runId=run["id"])
            runner.write_state(path, state)
        for row in state["outcomes"]:
            self.apply(row, state["runId"])

    def apply(self, row, run_id):
        for job, state in self.states():
            if state.get("keeps") or row["itemId"] != self.runner.filed_printing(state):
                continue
            state["aliasRun"] = run_id
            if row.get("status") == "verified":
                state.update(alias=row["shortAlias"], aliasItem=row["itemId"], aliasRun=run_id)
                if "alias" not in state.setdefault("done", []):
                    state["done"].append("alias")
            elif not state.get("alias"):
                state["error"] = row.get("error") or "Kurzlink nicht bestätigt."
            runner.write_state(self.runner.root / job, state)

    def alias_pr(self):
        self.runner.prepare()
        path = self.runner.data / "data/social.json"
        rows = read_social(self.runner.data)
        items, changed = [], False
        for _job, state in self.states():
            if state.get("keeps"):
                continue
            item = self.runner.filed_printing(state)
            if state.get("aliasItem") != item or state["alias"] != select_keyword(rows, item, None):
                raise runner.RunError("Der bestätigte Kurzlink gehört nicht mehr zur eingefrorenen Zuordnung.")
            items.append(item)
            changed |= rows[item].get("shortAlias") != state["alias"]
            rows[item]["shortAlias"] = state["alias"]
        if changed:
            path.write_text(json.dumps(list(rows.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            self.runner.git(self.runner.data, "switch", "-q", "-C", self.state["branch"])
            self.runner.check_script("scripts/regen.py")
            message = "Record the nightly batch's verified short links (#679)"
            self.runner.git(self.runner.data, "add", "-A")
            self.runner.git(self.runner.data, "commit", "-q", "-m", message)
            self.runner.check_script("verification/publication_audit.py")
            self.runner.publish_branch(self.folder, self.state, "aliasPr", self.state["branch"], message, message)
            self.save()
            self.runner.land(self.state["aliasPr"], self.state.get("aliasPrHead"), self.state.get("pushed", []))
        if changed or self.state.get("aliasPr"):
            defer(self.runner, items)
        for job, state in self.states():
            state["aliasPr"] = self.state.get("aliasPr")
            runner.write_state(self.runner.root / job, state)

    def fail(self, message):
        self.state.update(status="failed", error=message, finishedAt=runner.now())
        self.save()
        for job, state in self.states():
            if self.state.get("publishRun"):
                state["publishRun"] = self.state["publishRun"]
            runner.write_state(self.runner.root / job, dict(state, status="failed", error=message,
                                                           finishedAt=runner.now()))
