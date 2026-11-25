"""Intake without an agent on the Homelab (#659, owner decisions of 2026-11-24 in #654).

A job with its printing, approved corners and a passed number check is filed by `intake.py` in the
runner's own clones, and then, without an agent: its pull request is merged on green CI, `Publish site`
runs, `Provision Snoredex short links` verifies the card's alias, and the alias is recorded in a second
pull request merged on green CI. The Posts tab builds the draft once `sync` has pulled main.

Every finished step is written beside the job (`intake-run.json`), so a run that stops anywhere starts
again where it stopped: the archive copy is found again by its bytes (`intake.py`), an existing pull
request is reused, a merged one is not merged twice, a recorded alias is not recorded twice.

A workflow is dispatched once and followed by the id of the run GitHub started (#673), never by its
time: a foreign run of the same workflow decides nothing here. The dispatch is written beside the job
before GitHub hears of it, with a request token the run carries in its title, so an answer lost on the
way is found again by that title. A new dispatch follows only a run that clearly failed, or a dispatch
that clearly started none.

An approval holds for exactly one printing (#672, owner decision D01): queuing freezes the photo, its
printing and its corners beside the run. Intake starts only on unchanged inputs, and before anything
leaves for the printing (the short link, the alias PR) the run checks that main filed its SPEC for the
frozen printing. A run from before the freeze takes the printing main filed its SPEC for.

Access lives only in the Homelab's environment (#654): `INTAKE_GITHUB_TOKEN`, a token for pull
requests, merges and workflow runs in snoredex-data, and `PHOTOS_DEPLOY_KEY`, the path of a deploy key
for snoredex-photos only.
"""

from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4
import zipfile

from overview import Catalogue

REPO = "m4s-ai/snoredex-data"
DATA_URL = f"https://github.com/{REPO}.git"
PHOTOS_URL = "ssh://github.com/m4s-ai/snoredex-photos.git"  # as user git, set in GIT_SSH_COMMAND
# git asks for the token through this script, which reads it from the environment: never a file or argv
ASKPASS = '#!/bin/sh\ncase "$1" in Username*) echo x-access-token ;; *) echo "$INTAKE_GITHUB_TOKEN" ;; esac\n'
STATE = "intake-run.json"
WORK = ".work"  # the runner's own clones in the private data folder; the page lists hash folders only
STEPS = ("intake", "merge", "publish", "alias", "alias-pr")
FAILED = {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"}
# GitHub lists a run as it accepts its dispatch: a request token no listed run carries after this started none
GRACE = timedelta(minutes=10)
IDENTITY = {"GIT_AUTHOR_NAME": "SnoreDex inbox", "GIT_COMMITTER_NAME": "SnoreDex inbox",
            "GIT_AUTHOR_EMAIL": "snoredex-inbox@users.noreply.github.com",
            "GIT_COMMITTER_EMAIL": "snoredex-inbox@users.noreply.github.com"}


class RunError(Exception):
    """A step that cannot finish; the message is shown at the job, in the inbox's language."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_state(folder):
    path = Path(folder) / STATE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_state(folder, state):
    path = Path(folder) / STATE
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(state, updatedAt=now()), indent=1) + "\n", encoding="utf-8", newline="\n")
    for attempt in range(50):  # Windows refuses the replace while the page reads the file; Linux never
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 49:
                raise
            time.sleep(0.05)


def approval(folder):
    """What "Übernehmen" approves: the photo, its printing and its corners, as the job holds them now."""
    path = Path(folder) / "job.json"
    job = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return {"photoSha256": job.get("sha256") or Path(folder).name, "itemId": job.get("itemId"),
            "corners": job.get("corners"), "cornersApprovedAt": job.get("cornersApprovedAt"), "approvedAt": now()}


def assignment_lock(state):
    """Why the printing and the corners may not change now, or None (D01): from "Übernehmen" until the
    run ends, and for good once the run filed its SPEC for the approved printing."""
    if "intake" in state.get("done", []):
        return (f"Gesperrt: {state.get('specimen')} ist für diesen Druck angelegt. Ist die Zuordnung falsch, "
                "muss diese SPEC im Katalog korrigiert werden.")
    if state.get("status") in ("queued", "running"):
        return ("Gesperrt, solange die Übernahme läuft. Hält sie vor dem Anlegen an, lassen sich Druck und "
                "Ecken wieder ändern.")
    return None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # an artifact's storage URL gets no token
        return None


class GitHub:
    """The few REST calls the run needs, with the token from the environment."""

    def __init__(self, token, repo=REPO, api="https://api.github.com"):
        self.token, self.base, self.opener = token, f"{api}/repos/{repo}", build_opener(NoRedirect)
        self.owner = repo.split("/")[0]

    def call(self, method, path, body=None):
        request = Request(self.base + path, method=method, data=json.dumps(body).encode() if body else None,
                          headers={"Accept": "application/vnd.github+json", "Authorization": "token " + self.token,
                                   "X-GitHub-Api-Version": "2022-11-28"})
        try:
            with self.opener.open(request, timeout=60) as response:
                raw = response.read()
        except HTTPError as error:
            if error.code in (301, 302, 303, 307):
                return {"location": error.headers["Location"]}
            raise RunError(f"GitHub {method} {path}: {error.code} {error.read()[:200].decode(errors='replace')}")
        return json.loads(raw) if raw else {}

    def pull_for(self, branch):
        pulls = self.call("GET", f"/pulls?state=all&head={self.owner}:{branch}")
        return pulls[0] if pulls else None

    def open_pull(self, branch, title, body):
        return self.call("POST", "/pulls", {"title": title, "head": branch, "base": "main", "body": body})

    def pull(self, number):
        return self.call("GET", f"/pulls/{number}")

    def checks(self, sha):
        """success, failure or pending for every check run on a commit; none yet is pending."""
        runs = self.call("GET", f"/commits/{sha}/check-runs?per_page=100")["check_runs"]
        if not runs or any(run["status"] != "completed" for run in runs):
            return "pending"
        return "failure" if any(run["conclusion"] in FAILED for run in runs) else "success"

    def merge(self, number, sha):
        self.call("PUT", f"/pulls/{number}/merge", {"sha": sha, "merge_method": "merge"})

    def dispatch(self, workflow, inputs):
        """Start a workflow on main; the id of the run GitHub started, or None when its answer names none."""
        answer = self.call("POST", f"/actions/workflows/{workflow}/dispatches",
                           {"ref": "main", "inputs": inputs, "return_run_details": True})
        return answer.get("workflow_run_id")

    def run(self, run_id):
        return self.call("GET", f"/actions/runs/{run_id}")

    def runs_titled(self, workflow, request, dispatched_at):
        """The ids of the dispatched runs on main whose title carries `request`, or None when GitHub did not
        list them all. The list reaches a day before the dispatch, so a clock off by hours still finds it."""
        since = (datetime.fromisoformat(dispatched_at) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        found = self.call("GET", f"/actions/workflows/{workflow}/runs?event=workflow_dispatch&branch=main"
                                 f"&per_page=100&created={quote('>=' + since)}")
        if found["total_count"] > len(found["workflow_runs"]):
            return None
        return [run["id"] for run in found["workflow_runs"] if request in (run.get("display_title") or "")]

    def artifact(self, run_id, name):
        """The bytes of a run's artifact, or None when the run left none."""
        found = self.call("GET", f"/actions/runs/{run_id}/artifacts")["artifacts"]
        artifact = next((item for item in found if item["name"] == name), None)
        if artifact is None:
            return None
        location = self.call("GET", f"/actions/artifacts/{artifact['id']}/zip")["location"]
        with build_opener().open(location, timeout=120) as response:
            return response.read()


class Runner:
    """One run at a time, in order; the page and the nightly round only queue job ids."""

    def __init__(self, root, github, key=None, urls=(DATA_URL, PHOTOS_URL), sleep=time.sleep, poll=30,
                 patience=timedelta(minutes=45), grace=GRACE):
        self.root, self.github, self.sleep, self.poll, self.patience = Path(root), github, sleep, poll, patience
        self.grace = grace
        self.urls = urls
        self.data, self.photos = self.root / WORK / "snoredex-data", self.root / WORK / "snoredex-photos"
        self.env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS=str(self.root / WORK / "askpass.sh"),
                        **IDENTITY)
        if key:
            self.env["GIT_SSH_COMMAND"] = (f"ssh -i {key} -o User=git -o IdentitiesOnly=yes "
                                           "-o StrictHostKeyChecking=accept-new "
                                           f"-o UserKnownHostsFile={self.root / WORK / 'known_hosts'}")
        self.jobs, self.waiting = queue.Queue(), set()

    # --- the queue ------------------------------------------------------------------------------
    def submit(self, job_id):
        """Queue a job once; a queued or running job is not queued again. The button and the night both
        land here, so both freeze the approval; a run that filed already keeps the one it filed for."""
        if job_id in self.waiting:
            return False
        self.waiting.add(job_id)
        state = read_state(self.root / job_id)
        if "intake" not in state.get("done", []):
            state["approval"] = approval(self.root / job_id)
        write_state(self.root / job_id, dict(state, status="queued", error=None))
        self.jobs.put(job_id)
        return True

    def recover(self):
        """A run a restart cut off stops where it was; the button or the night starts it again."""
        for path in self.root.glob(f"*/{STATE}"):
            state = read_state(path.parent)
            if state.get("status") in ("queued", "running"):
                write_state(path.parent, dict(state, status="failed", error="Unterbrochen durch einen Neustart."))

    def start(self):
        self.recover()

        def loop():
            while True:
                job_id = self.jobs.get()
                try:
                    self.run(job_id)
                except Exception as error:  # noqa: BLE001 - one broken job must not stop the queue
                    print(f"Übernahme {job_id[:12]}: {error}", flush=True)
                finally:
                    self.waiting.discard(job_id)

        threading.Thread(target=loop, name="intake-runner", daemon=True).start()

    def nightly(self, ready, hour=3):
        """Each night at `hour` (UTC), queue every job `ready()` names, failed ones included."""
        def loop():
            while True:
                current = datetime.now(timezone.utc)
                due = current.replace(hour=hour, minute=0, second=0, microsecond=0)
                time.sleep(((due if due > current else due + timedelta(days=1)) - current).total_seconds())
                for job_id in ready():
                    self.submit(job_id)

        threading.Thread(target=loop, name="intake-nightly", daemon=True).start()

    # --- one run --------------------------------------------------------------------------------
    def run(self, job_id):
        folder = self.root / job_id
        if not (folder / "job.json").is_file():
            return  # moved to the trash after it was queued: nothing to file
        state = read_state(folder)
        state.setdefault("done", [])
        try:
            for name in STEPS:
                if name not in state["done"]:
                    state.update(step=name, error=None)
                    write_state(folder, dict(state, status="running"))
                    getattr(self, "step_" + name.replace("-", "_"))(folder, state)
                    state["done"].append(name)
                    write_state(folder, dict(state, status="running"))
            write_state(folder, dict(state, status="done", step=None, error=None))
        except (RunError, OSError, subprocess.SubprocessError, KeyError, ValueError) as error:
            write_state(folder, dict(state, status="failed", error=str(error) or type(error).__name__))

    def git(self, cwd, *args):
        done = subprocess.run(["git", "-C", str(cwd), *args], env=self.env, capture_output=True, text=True,
                              timeout=600)
        if done.returncode:
            raise RunError(f"git {args[0]}: {(done.stderr or done.stdout).strip()[-300:]}")
        return done.stdout.strip()

    def prepare(self):
        """Both clones at origin/main with nothing of an earlier run left; they are the runner's own."""
        askpass = Path(self.env["GIT_ASKPASS"])
        askpass.parent.mkdir(parents=True, exist_ok=True)
        askpass.write_text(ASKPASS, encoding="utf-8", newline="\n")
        askpass.chmod(0o700)
        for url, path in zip(self.urls, (self.data, self.photos)):
            if not (path / ".git").is_dir():
                path.parent.mkdir(parents=True, exist_ok=True)
                self.git(path.parent, "clone", "-q", url, path.name)
            self.git(path, "fetch", "-q", "origin")
            self.git(path, "checkout", "-q", "-f", "-B", "main", "origin/main")
            self.git(path, "clean", "-q", "-fd")
            # a branch an earlier attempt left would stop intake.py's own `switch -c intake/SPEC-nnnn`
            for branch in self.git(path, "for-each-ref", "--format=%(refname:short)", "refs/heads/").split():
                if branch != "main":
                    self.git(path, "branch", "-q", "-D", branch)

    def step_intake(self, folder, state):
        job, approved = json.loads((folder / "job.json").read_text(encoding="utf-8")), state.get("approval") or {}
        if not approved.get("itemId") or [job.get(key) for key in ("itemId", "corners")] != [
                approved["itemId"], approved.get("corners")]:
            raise RunError("Druck oder Ecken weichen von der Freigabe bei „Übernehmen“ ab. "
                           "Bitte prüfen, dann „Erneut versuchen“.")
        self.prepare()
        done = subprocess.run([sys.executable, str(self.data / "verification/photo_inbox/intake.py"), str(folder),
                               "--photos", str(self.photos)], cwd=self.data, env=self.env, capture_output=True,
                              text=True, timeout=1800)
        if done.returncode:
            lines = (done.stderr or done.stdout).strip().splitlines()
            raise RunError(lines[-1] if lines else f"intake.py endete mit {done.returncode}")
        branch = done.stdout.strip().splitlines()[-1]
        state["specimen"] = branch.split("/", 1)[1]
        state["pr"] = self.publish_branch(self.data, branch, f"File {state['specimen']} from the photo inbox (#656)",
                                          self.git(self.data, "log", "-1", "--format=%B"))

    def publish_branch(self, checkout, branch, title, message):
        """Push the runner's branch and reuse or open its pull request; returns its number."""
        self.git(checkout, "push", "-q", "-f", "origin", f"HEAD:refs/heads/{branch}")
        pull = self.github.pull_for(branch)
        if pull is None or pull["state"] == "closed" and not pull.get("merged_at"):
            pull = self.github.open_pull(branch, title, f"{message}\n\nOpened by the photo inbox's intake run (#659).")
        return pull["number"]

    def step_merge(self, _folder, state):
        self.land(state["pr"])

    def land(self, number):
        """Merge a pull request once its checks are green; a red check stops the run with its link."""
        deadline = datetime.now(timezone.utc) + self.patience
        while datetime.now(timezone.utc) < deadline:
            pull = self.github.pull(number)
            if pull.get("merged_at"):
                return
            result = self.github.checks(pull["head"]["sha"])
            if result == "failure":
                raise RunError(f"Die CI von PR #{number} ist rot: {pull['html_url']}")
            if result == "success":
                self.github.merge(number, pull["head"]["sha"])
                return
            self.sleep(self.poll)
        raise RunError(f"PR #{number} wurde nicht rechtzeitig grün: {pull['html_url']}")

    def workflow(self, folder, state, name, inputs):
        """Start a workflow on main once and wait for exactly the run it started (#673); anything but
        success stops the run. A run that clearly failed is forgotten, so the next start dispatches anew;
        one still running, or not found yet, is waited for again by the next start."""
        record = self.dispatched(folder, state, name, inputs)
        deadline = datetime.now(timezone.utc) + self.patience
        while True:
            run = self.own_run(folder, state, name, record)
            if run and run["status"] == "completed":
                if run["conclusion"] != "success":
                    del state["runs"][name]
                    raise RunError(f"{name} endete mit {run['conclusion']}: {run['html_url']}")
                return run
            if datetime.now(timezone.utc) >= deadline:
                raise RunError(f"{name} wurde nicht rechtzeitig fertig: {run['html_url']}" if run else
                               f"{name}: Ob GitHub den Lauf gestartet hat, ist ungeklärt. „Erneut versuchen“ "
                               "sucht ihn wieder; neu gestartet wird erst, wenn sicher keiner läuft.")
            self.sleep(self.poll)

    def dispatched(self, folder, state, name, inputs):
        """This job's dispatch of the workflow: the earlier one, or a new one written down before GitHub
        hears of it, with the request token the run carries in its title."""
        runs = state.setdefault("runs", {})
        record = runs.get(name)
        if record and not record["runId"] and self.never_started(name, record):
            record = None
        if record is None:
            record = runs[name] = {"request": "inbox-" + uuid4().hex[:16], "dispatchedAt": now(), "runId": None}
            write_state(folder, dict(state, status="running"))
            record["runId"] = self.github.dispatch(name, dict(inputs, request=record["request"]))
            write_state(folder, dict(state, status="running"))
        return record

    def never_started(self, name, record):
        """Certain that a dispatch whose answer went missing started no run: the grace is over and GitHub
        lists every run since, none of them with the request token."""
        waited = datetime.now(timezone.utc) - datetime.fromisoformat(record["dispatchedAt"])
        return waited >= self.grace and self.github.runs_titled(name, record["request"], record["dispatchedAt"]) == []

    def own_run(self, folder, state, name, record):
        """The run the dispatch started; while GitHub's answer is missing, the one run titled with the
        request token, else None."""
        if not record["runId"]:
            found = self.github.runs_titled(name, record["request"], record["dispatchedAt"])
            if not found or len(found) > 1:
                return None
            record["runId"] = found[0]
            write_state(folder, dict(state, status="running"))
        return self.github.run(record["runId"])

    def step_publish(self, folder, state):
        self.workflow(folder, state, "pages.yml", {})

    def printing(self, state):
        """The printing this run delivers to, checked on main before anything leaves for it: main must
        file the run's SPEC for the frozen printing. A run from before the freeze takes main's."""
        self.prepare()
        filed = Catalogue(self.data).filed_item(state["specimen"])
        if filed is None:
            raise RunError(f"Auf main ist {state['specimen']} keinem Druck eindeutig zugeordnet. "
                           "Bitte den Katalog prüfen, dann „Erneut versuchen“.")
        frozen = (state.get("approval") or {}).get("itemId") or filed
        if filed != frozen:
            raise RunError(f"Auf main gehört {state['specimen']} zu einem anderen Druck als bei „Übernehmen“ "
                           "freigegeben. Der Lauf hält an, bevor etwas für den Druck rausgeht; bitte den Katalog "
                           "prüfen.")
        return frozen

    def step_alias(self, folder, state):
        item_id = self.printing(state)
        run = self.workflow(folder, state, "yourls-pilot.yml", {"item_ids": item_id})
        found = self.github.artifact(run["id"], "yourls-verified")
        del state["runs"]["yourls-pilot.yml"]  # the run has answered; another verification is another run
        if found is None:
            raise RunError("Der Lauf hat kein Ergebnis yourls-verified hinterlassen.")
        with zipfile.ZipFile(BytesIO(found)) as archive:
            result = json.loads(archive.read("yourls-result.json"))
        if result.get("status") != "verified" or result.get("itemId") != item_id:
            raise RunError(f"Der Kurzlink wurde nicht bestätigt: {result.get('status')}")
        state["alias"], state["aliasItem"] = result["shortAlias"], item_id

    def step_alias_pr(self, folder, state):
        item_id = self.printing(state)
        if state.get("aliasItem") != item_id:  # verified for another printing, or before #672 said for which
            self.step_alias(folder, state)
        path = self.data / "data/social.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        row = next((row for row in rows if row["itemId"] == item_id), None)
        if row is None:
            raise RunError("Der Druck hat auf main keine Share-Zeile.")
        if row.get("shortAlias") == state["alias"]:
            return  # recorded already, by this run before it stopped or by hand
        row["shortAlias"] = state["alias"]
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        branch = f"intake/{state['specimen']}-alias"
        self.git(self.data, "switch", "-q", "-C", branch)
        done = subprocess.run([sys.executable, "scripts/regen.py"], cwd=self.data, env=self.env,
                              capture_output=True, text=True, timeout=1800)
        if done.returncode:
            raise RunError("regen.py schlägt fehl: " + ((done.stdout + done.stderr).strip().splitlines() or ["?"])[-1])
        message = (f"Record the verified short link of {state['specimen']}\n\n{item_id} -> {state['alias']}, "
                   "verified by Provision Snoredex short links (#659).")
        self.git(self.data, "add", "-A")
        self.git(self.data, "commit", "-q", "-m", message)
        state["aliasPr"] = self.publish_branch(self.data, branch, f"Record the short link of {state['specimen']}",
                                               message)
        self.land(state["aliasPr"])
