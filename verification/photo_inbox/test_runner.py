"""The intake run without an agent (#659), against local Git remotes and a stand-in GitHub.

The real intake.py, check.py and regen.py are tested on their own (test_intake.py); here a stand-in
intake.py in the remote does what the run relies on: push the archive copy, commit on intake/SPEC-nnnn,
print the branch, or refuse with a reason. Checked: the whole chain, a restart after every failure
without a second intake, pull request or merge, red CI, a refusal, an alias already on main, a run a
restart cut off, and the page's button. The stand-in GitHub answers a dispatch as GitHub does, with the
id of the run it started, and titles each run by its workflow's run-name (#673).
Published orders also return through the worker's permalink PR (#646): once per link, surviving a
lost merge answer, guarded by the local gate, the required CI and the ownership of the remote branch.

    python verification/photo_inbox/test_runner.py
"""

from datetime import timedelta
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app as inbox  # noqa: E402
import runner  # noqa: E402

ITEM = "item-c25516ed-66e0-5cb1-9b96-5fa22e4c99be"
OTHER = "item-7cf9c091-8e34-58a1-9185-ff3c7f6bcfd6"
SOURCE_FIRST = "item-9fd9f124-e143-550d-bc3c-27e26ca0bdb7"  # no legacy printing: cited by its source-first key
PRINTINGS = {ITEM: "printing-a", OTHER: "printing-b", SOURCE_FIRST: None}
JOB = "a" * 64
TITLES = {"pages.yml": "Publish site", "yourls-pilot.yml": "Provision Snoredex short links"}  # run-name
# the stand-in files the SPEC for the job's printing, cited the way the catalogue maps it back
FAKE_INTAKE = '''import json, os, pathlib, subprocess, sys
data, photos, job = pathlib.Path.cwd(), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[1])
count = pathlib.Path(os.environ["FAKE_COUNT"])
count.write_text(str(int(count.read_text() or 0) + 1) if count.exists() else "1")
if os.environ.get("FAKE_REFUSE"):
    print("Übernahme zurückgestellt: Die Kartenecken sind noch nicht freigegeben.", file=sys.stderr)
    sys.exit(2)
if not (photos / "SPEC-0001.jpg").exists():  # an earlier attempt's copy is reused, as intake.py does
    (photos / "SPEC-0001.jpg").write_bytes(b"photo")
    for args in (["add", "-A"], ["commit", "-q", "-m", "SPEC-0001"], ["push", "-q"]):
        subprocess.run(["git", "-C", str(photos), *args], check=True)
subprocess.run(["git", "switch", "-q", "-c", "intake/SPEC-0001", "origin/main"], check=True)
item = json.loads((job / "job.json").read_text(encoding="utf-8"))["itemId"]
row = next(row for row in json.loads((data / "collector_catalogue.json").read_text())["items"] if row["itemId"] == item)
cited = row["sourcePrintingId"] or next(ref.removeprefix("CLAIM:source-first:") for ref in row["sourceClaimRefs"]
                                       if ref.startswith("CLAIM:source-first:"))
(data / "verification/specimens.json").write_text(json.dumps({"specimens": [
    {"specimenId": "SPEC-0001", "photographedBy": "collection owner", "citedBy": [cited]}]}))
if not os.environ.get("FAKE_PRIVATE"):  # regen.py rebuilds a page Pages serves
    (data / "index.html").write_text("SPEC-0001\\n")
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-q", "-m", "File SPEC-0001"], check=True)
keeps = os.environ.get("FAKE_KEEPS") or None  # the printing's image is already this owner photo
pathlib.Path(sys.argv[sys.argv.index("--result") + 1]).write_text(json.dumps(
    {"branch": "intake/SPEC-0001", "specimen": "SPEC-0001", "itemId": item, "keeps": keeps}))
print("intake/SPEC-0001")
'''


class Crash(BaseException):
    """The inbox dies mid-call: nothing of the run catches it, only what is on disk survives."""


def alias(item):
    """The alias Provision Snoredex short links gives a printing: its id's first two groups."""
    return "sd" + item[5:13] + item[14:18]


def git(*args):
    env = dict(os.environ, **runner.IDENTITY)
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True, env=env).stdout.strip()


def remote(temp, name, files):
    """A bare remote with one commit on main holding `files`."""
    seed, bare = Path(temp) / f"{name}-seed", Path(temp) / f"{name}.git"
    git("init", "-q", "-b", "main", str(seed))
    for path, text in files.items():
        (seed / path).parent.mkdir(parents=True, exist_ok=True)
        (seed / path).write_text(text, encoding="utf-8", newline="\n")
    git("-C", str(seed), "add", "-A")
    git("-C", str(seed), "commit", "-q", "-m", "seed")
    git("clone", "-q", "--bare", str(seed), str(bare))
    return str(bare)


class StandIn:
    """GitHub as the run sees it: pull requests, checks, merges, dispatched workflows, an artifact."""

    def __init__(self, data_remote, checks="success", fail_dispatch=0, fail_open=0):
        self.remote, self.result, self.fail_dispatch, self.fail_open = data_remote, checks, fail_dispatch, fail_open
        self.pulls, self.merged, self.dispatched, self.opened = {}, [], [], 0
        # runs GitHub keeps, the (looks until done, conclusion) of the next dispatches, and the faults
        self.runs, self.script, self.lose_answer, self.no_answer, self.lag, self.fail_poll = [], {}, 0, False, 0, 0
        self.wrong_artifact = False
        self.required = [("gate (ubuntu-latest)", 15368), ("gate (windows-latest)", 15368)]  # main's ruleset
        self.stale_heads = []  # heads GitHub still reports for a PR just after a push

    def pull_for(self, branch):
        return next((pull for pull in self.pulls.values() if pull["branch"] == branch), None)

    def open_pull(self, branch, title, body):
        if self.fail_open:
            self.fail_open -= 1
            raise runner.RunError("GitHub POST /pulls: 502")
        self.opened += 1
        number = 100 + len(self.pulls)
        self.pulls[number] = {"number": number, "branch": branch, "state": "open", "merged_at": None,
                              "html_url": f"https://example.invalid/pull/{number}", "title": title}
        return self.pulls[number]

    def pull(self, number):
        pull = self.pulls[number]
        sha = self.stale_heads.pop(0) if self.stale_heads else git("--git-dir", self.remote, "rev-parse", pull["branch"])
        return dict(pull, head={"sha": sha})

    def required_checks(self):
        return self.required

    def checks(self, _sha, required):
        assert required == self.required, "the checks main requires decide"
        return self.result

    def merge(self, number, sha):
        pull = self.pulls[number]
        assert sha == git("--git-dir", self.remote, "rev-parse", pull["branch"]), "merged at the checked head"
        git("--git-dir", self.remote, "update-ref", "refs/heads/main", sha)  # fast-forward: the branch is on main
        pull.update(merged_at="2026-11-25T12:00:00Z", state="closed")
        self.merged.append(number)

    def start_run(self, workflow, inputs, looks=0, conclusion="success"):
        """A run as GitHub keeps it: titled by its workflow's run-name, done after `looks` looks at it."""
        number = 9000 + len(self.runs)
        self.runs.append({"id": number, "workflow": workflow, "inputs": inputs, "looks": looks,
                          "conclusion": conclusion, "display_title": f"{TITLES[workflow]} {inputs.get('request', '')}",
                          "html_url": f"https://example.invalid/runs/{number}"})
        return self.runs[-1]

    def dispatch(self, workflow, inputs):
        if self.fail_dispatch:
            self.fail_dispatch -= 1
            raise runner.RunError(f"GitHub POST {workflow}: 500")  # refused: no run started
        assert inputs["request"].startswith("inbox-"), inputs
        run = self.start_run(workflow, inputs, *(self.script.get(workflow) or [(0, "success")]).pop(0))
        self.dispatched.append((workflow, {key: value for key, value in inputs.items() if key != "request"}))
        if self.lose_answer:
            self.lose_answer -= 1
            raise Crash  # accepted, and the inbox died before the answer arrived
        return None if self.no_answer else run["id"]

    def run(self, run_id):
        if self.fail_poll:
            self.fail_poll -= 1
            raise Crash  # the inbox restarts while it waits for the run
        run = next(run for run in self.runs if run["id"] == run_id)
        if run["looks"]:
            run["looks"] -= 1
            return dict(run, status="in_progress", conclusion=None)
        return dict(run, status="completed")

    def runs_titled(self, workflow, request, _dispatched_at):
        if self.lag:  # GitHub lists the run a moment after it accepted the dispatch
            self.lag -= 1
            return []
        return [run["id"] for run in self.runs if run["workflow"] == workflow and request in run["display_title"]]

    def artifact(self, run_id, name):
        assert name == "yourls-verified"
        run = next(run for run in self.runs if run["id"] == run_id)
        item = OTHER if self.wrong_artifact else run["inputs"]["item_ids"]  # the run's own printing
        out = BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            archive.writestr("yourls-result.json", json.dumps(
                {"itemId": item, "shortAlias": alias(item), "status": "verified"}))
        return out.getvalue()


def setup(temp, alias=None):
    social = [{"itemId": ITEM, "specimenId": "SPEC-0001", "instagramPosts": [],
               **({"shortAlias": alias} if alias else {})},
              {"itemId": SOURCE_FIRST, "specimenId": "SPEC-0002", "instagramPosts": []}]
    catalogue = {"meta": {"assetBaseUrl": "https://example.invalid/", "dataAsOf": "2026-11-25"},
                 "localizations": [{"localizationId": "en", "displayName": "English"}], "assets": [],
                 "items": [{"itemId": item, "active": True, "localizationId": "en", "cardName": "Snorlax",
                            "sourcePrintingId": printing, "sourceClaimRefs": [] if printing else
                            ["CLAIM:specimen:SPEC-0002", "CLAIM:source-first:key-c"]}
                           for item, printing in PRINTINGS.items()]}
    data = remote(temp, "data", {"verification/photo_inbox/intake.py": FAKE_INTAKE,
                                 "scripts/regen.py": "import os, sys; sys.exit(bool(os.environ.get('FAKE_GATE_FAIL')))\n",
                                 "verification/publication_audit.py": "",
                                 "data/social.json": json.dumps(social, indent=2) + "\n",
                                 "collector_catalogue.json": json.dumps(catalogue),
                                 "verification/specimens.json": json.dumps({"specimens": []}),
                                 "data/images.json": json.dumps({"galleryImages": []})})
    photos = remote(temp, "photos", {"README.md": "archive\n"})
    root = Path(temp) / "inbox"
    (root / JOB).mkdir(parents=True)
    write_job(root, itemId=ITEM)
    os.environ["FAKE_COUNT"] = str(Path(temp) / "intake-count")
    return root, data, photos


def write_job(root, **changes):
    path = root / JOB / "job.json"
    job = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"id": JOB, "file": "photo.dng"}
    path.write_text(json.dumps(dict(job, **changes)), encoding="utf-8", newline="\n")


def make(root, github, data, photos, **options):
    """A runner that never sleeps; a dispatch that started no run is past its grace unless a test says."""
    return runner.Runner(root, github, urls=(data, photos), sleep=lambda _seconds: None, poll=0,
                         **dict({"grace": timedelta(0)}, **options))


def go(root, github, data, photos, **options):
    """The owner's "Übernehmen": queue (which freezes the approval), then run."""
    run = make(root, github, data, photos, **options)
    run.submit(JOB)
    run.run(JOB)


def recite(data_remote, temp, cited):
    """A later commit on main that cites SPEC-0001 differently, as a catalogue correction would."""
    work = Path(temp) / "recite"
    git("clone", "-q", data_remote, str(work))
    path = work / "verification/specimens.json"
    specimens = json.loads(path.read_text(encoding="utf-8"))
    specimens["specimens"][0]["citedBy"] = cited
    path.write_text(json.dumps(specimens), encoding="utf-8", newline="\n")
    git("-C", str(work), "commit", "-q", "-am", "recite SPEC-0001")
    git("-C", str(work), "push", "-q", "origin", "HEAD:main")


def social_on(data_remote, ref):
    return json.loads(git("--git-dir", data_remote, "show", f"{ref}:data/social.json"))


def posted(root, field="ig:snoredex", url="https://www.instagram.com/p/abc/"):
    path = root / ".posts/SPEC-0001/order.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    order = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"itemId": ITEM, "targets": {}}
    order["targets"][field] = {"status": "published", "permalink": url}
    path.write_text(json.dumps(order), encoding="utf-8", newline="\n")


def permalink_feedback():
    """A published target returns through one checked PR, including after a lost merge answer."""
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data)
        run = make(root, github, data, photos)
        run.record_posts()
        assert github.opened == 0 and not run.data.exists(), "no published order: no Git or API work"
        posted(root)
        posted(root, "fb_page:1", "https://www.facebook.com/1/posts/2")
        merge = github.merge

        def lost_answer(number, sha):
            merge(number, sha)
            raise Crash

        github.merge = lost_answer
        try:
            run.record_posts()
        except Crash:
            pass
        else:
            raise AssertionError("the process died after GitHub merged")
        github.merge = merge
        run = make(root, github, data, photos)  # only disk survives the restart
        run.record_posts()
        row = social_on(data, "main")[0]
        saved = runner.read_state(root / runner.WORK / "permalinks")
        assert saved["pr"] == 100 and saved["prHead"], "the merge remains traceable after the lost answer"
        assert row["instagramPosts"] == ["https://www.instagram.com/p/abc/"]
        assert row["facebookPosts"] == ["https://www.facebook.com/1/posts/2"]
        assert "threadsPosts" not in row and github.opened == 1 and len(github.merged) == 1
        assert github.dispatched == [], "the permalink PR alone authorizes no Pages run"
        run.prepare = lambda: (_ for _ in ()).throw(AssertionError("finished orders cost no Git/API work"))
        before = (root / runner.WORK / "permalinks" / runner.STATE).read_bytes()
        run.process_next(timeout=0)  # the idle worker, rather than a button or an agent, runs the import
        assert (root / runner.WORK / "permalinks" / runner.STATE).read_bytes() == before
        posted(root, "threads:snoredex", "https://www.threads.com/@snoredex/post/xyz")
        make(root, github, data, photos).record_posts()
        row = social_on(data, "main")[0]
        assert row["threadsPosts"] == ["https://www.threads.com/@snoredex/post/xyz"]
        assert github.opened == 2 and len(github.merged) == 2, "later target adds one PR, keeps earlier links"


def permalink_failure():
    """Red CI remains unmerged; a retry reuses the branch/PR and never overwrites a foreign head."""
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data, checks="failure")
        posted(root)
        make(root, github, data, photos).record_posts()
        folder = root / runner.WORK / "permalinks"
        state = runner.read_state(folder)
        assert state["status"] == "failed" and "ist rot" in state["error"]
        assert not social_on(data, "main")[0]["instagramPosts"] and github.opened == 1
        posted(root, "threads:snoredex", "https://www.threads.com/@snoredex/post/later")
        github.result = "success"
        make(root, github, data, photos).record_posts()
        assert runner.read_state(folder)["status"] == "done" and github.opened == 1
        assert "threadsPosts" not in social_on(data, "main")[0], "finish the frozen batch first"
        make(root, github, data, photos).record_posts()
        assert social_on(data, "main")[0]["threadsPosts"] == ["https://www.threads.com/@snoredex/post/later"]
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data, fail_open=1)
        posted(root)
        run = make(root, github, data, photos)
        run.record_posts()
        branch = runner.read_state(root / runner.WORK / "permalinks")["branch"]
        work = Path(temp) / "foreign"
        git("clone", "-q", "-b", branch, data, str(work))
        (work / "foreign.txt").write_text("someone else's work\n", encoding="utf-8", newline="\n")
        git("-C", str(work), "add", "-A")
        git("-C", str(work), "commit", "-q", "-m", "foreign change")
        git("-C", str(work), "push", "-q")
        foreign = git("--git-dir", data, "rev-parse", branch)
        make(root, github, data, photos).record_posts()
        state = runner.read_state(root / runner.WORK / "permalinks")
        assert state["status"] == "failed" and "fremden Stand" in state["error"], state
        assert git("--git-dir", data, "rev-parse", branch) == foreign and not github.merged


def permalink_local_gate():
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data)
        posted(root)
        os.environ["FAKE_GATE_FAIL"] = "1"
        try:
            make(root, github, data, photos).record_posts()
        finally:
            del os.environ["FAKE_GATE_FAIL"]
        state = runner.read_state(root / runner.WORK / "permalinks")
        assert state["status"] == "failed" and "regen.py" in state["error"]
        assert not github.opened and not git("--git-dir", data, "branch", "--list", "posts/*")
        make(root, github, data, photos).record_posts()
        assert github.opened == 1 and len(github.merged) == 1


def whole_chain():
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data)
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "done" and state["done"] == list(runner.STEPS), state
        assert state["specimen"] == "SPEC-0001" and state["alias"] == "sdc25516ed66e0", state
        assert github.merged == [state["pr"], state["aliasPr"]], "both pull requests merged on green CI"
        assert github.dispatched == [("pages.yml", {}), ("yourls-pilot.yml", {"item_ids": ITEM})]
        assert social_on(data, "main")[0]["shortAlias"] == "sdc25516ed66e0", "the alias is recorded on main"
        assert git("--git-dir", photos, "ls-tree", "--name-only", "main") == "README.md\nSPEC-0001.jpg"
        assert git("--git-dir", data, "log", "-1", "--format=%ae", "main").endswith("noreply.github.com")


def restart_after_failure():
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data, fail_dispatch=1)
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "publish" and "500" in state["error"], state
        go(root, github, data, photos)
        assert runner.read_state(root / JOB)["status"] == "done"
        assert Path(os.environ["FAKE_COUNT"]).read_text() == "1", "the photo is filed once"
        assert github.opened == 2 and len(github.merged) == 2, "no pull request opened or merged twice"


def retry_after_failed_delivery():
    """The filing committed but its pull request did not open: the retry files again in the same clones."""
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data, fail_open=1)
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "intake" and "502" in state["error"], state
        go(root, github, data, photos)
        assert runner.read_state(root / JOB)["status"] == "done", runner.read_state(root / JOB)
        assert git("--git-dir", photos, "rev-list", "--count", "main") == "2", "one archive copy, reused"
        assert [pull["branch"] for pull in github.pulls.values()].count("intake/SPEC-0001") == 1, "one PR"


def keeps_the_branch():
    """#674: a retry pushes over nothing but its own earlier commit, and merges only the head it pushed."""
    with TemporaryDirectory() as temp:  # someone pushed to the branch after the filing: it stays
        root, data, photos = setup(temp)
        github = StandIn(data, fail_open=1)
        go(root, github, data, photos)
        foreign = commit_on(data, temp, "intake/SPEC-0001")
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "intake" and "fremden Stand" in state["error"], state
        assert git("--git-dir", data, "rev-parse", "intake/SPEC-0001") == foreign and github.pulls == {}, state
    with TemporaryDirectory() as temp:  # main moved on: the re-filing replaces this run's own earlier push
        root, data, photos = setup(temp)
        github = StandIn(data, fail_open=1)
        go(root, github, data, photos)
        commit_on(data, temp, "main")
        go(root, github, data, photos)
        assert runner.read_state(root / JOB)["status"] == "done" and github.opened == 2, "intake PR and alias PR"
    with TemporaryDirectory() as temp:  # a commit lands on the open PR's branch while its CI is red
        root, data, photos = setup(temp)
        github = StandIn(data, checks="failure")
        go(root, github, data, photos)
        moved = commit_on(data, temp, "intake/SPEC-0001")
        github.result = "success"
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "merge" and "anderen Stand" in state["error"], state
        assert github.merged == [] and git("--git-dir", data, "rev-parse", "intake/SPEC-0001") == moved
    with TemporaryDirectory() as temp:  # merged by hand meanwhile: no new action
        root, data, photos = setup(temp)
        github = StandIn(data, checks="failure")
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        github.merge(state["pr"], state["prHead"])
        github.merged.clear()
        github.result = "success"
        go(root, github, data, photos)
        assert runner.read_state(root / JOB)["status"] == "done" and state["pr"] not in github.merged
    with TemporaryDirectory() as temp:  # just after a push GitHub still names this run's earlier commit
        root, data, photos = setup(temp)
        github = StandIn(data, checks="failure")
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        runner.write_state(root / JOB, dict(state, pushed=["e" * 40, *state["pushed"]]))
        github.result, github.stale_heads = "success", ["e" * 40]
        go(root, github, data, photos)
        assert runner.read_state(root / JOB)["status"] == "done" and github.merged[0] == state["pr"], "waited for it"
    with TemporaryDirectory() as temp:  # a main that requires no check proves nothing about the gate
        root, data, photos = setup(temp)
        github = StandIn(data)
        github.required = []
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and "keine Pflichtchecks" in state["error"] and github.merged == [], state


def commit_on(data_remote, temp, branch):
    """Someone else's commit on a branch of the data remote; returns its id."""
    work = Path(temp) / ("foreign-" + branch.replace("/", "-"))
    git("clone", "-q", "-b", branch, data_remote, str(work))
    (work / "foreign.txt").write_text(branch + "\n", encoding="utf-8", newline="\n")
    git("-C", str(work), "add", "-A")
    git("-C", str(work), "commit", "-q", "-m", "someone else's change")
    git("-C", str(work), "push", "-q", "origin", f"HEAD:{branch}")
    return git("-C", str(work), "rev-parse", "HEAD")


def worker_survives_a_trashed_job():
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        gone = "b" * 64
        (root / gone).mkdir()
        (root / gone / "job.json").write_text("{}", encoding="utf-8", newline="\n")
        run = make(root, StandIn(data), data, photos)
        run.recover = lambda: None  # started before both jobs are queued, as in the running inbox
        run.submit(gone)
        (root / gone / "job.json").unlink()
        (root / gone / runner.STATE).unlink()
        (root / gone).rmdir()  # moved to the trash while queued
        run.submit(JOB)
        run.start()
        for _ in range(600):
            if runner.read_state(root / JOB).get("status") in ("done", "failed"):
                break
            time.sleep(0.1)
        assert runner.read_state(root / JOB)["status"] == "done", "the next job still runs"


def red_ci_and_refusal():
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        go(root, StandIn(data, checks="failure"), data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "merge" and "ist rot" in state["error"], state
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        os.environ["FAKE_REFUSE"] = "1"
        try:
            go(root, StandIn(data), data, photos)
        finally:
            del os.environ["FAKE_REFUSE"]
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and "Kartenecken" in state["error"], state


def further_evidence():
    """#675, D03: a photo of a printing whose image is already an owner photo is filed once and ends there."""
    for alias_on_main in (None, "sdc25516ed66e0"):  # without a share row's alias, and with one
        with TemporaryDirectory() as temp:
            root, data, photos = setup(temp, alias=alias_on_main)
            before = social_on(data, "main")
            github = StandIn(data)
            os.environ["FAKE_KEEPS"] = "SPEC-0000"
            try:
                go(root, github, data, photos)
            finally:
                del os.environ["FAKE_KEEPS"]
            state = runner.read_state(root / JOB)
            assert state["status"] == "done" and state["keeps"] == "SPEC-0000", state
            assert Path(os.environ["FAKE_COUNT"]).read_text() == "1" and github.merged == [state["pr"]], state
            assert github.dispatched == [("pages.yml", {})], "the deploy, and no short link"
            assert social_on(data, "main") == before and "aliasPr" not in state, "the share rows stay as they were"
    with TemporaryDirectory() as temp:  # nothing Pages serves changed: no deploy either
        root, data, photos = setup(temp)
        github = StandIn(data)
        os.environ.update(FAKE_KEEPS="SPEC-0000", FAKE_PRIVATE="1")
        try:
            go(root, github, data, photos)
        finally:
            del os.environ["FAKE_KEEPS"], os.environ["FAKE_PRIVATE"]
        state = runner.read_state(root / JOB)
        assert state["status"] == "done" and state["publish"] is False and github.dispatched == [], state
    assert runner.public(["data/claims.json"]) and runner.public(["images/previews/SPEC-0001.png"])
    assert not runner.public(["verification/specimens.json", "images/notes.txt", "scripts/build.py"])


def alias_already_recorded():
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp, alias="sdc25516ed66e0")
        github = StandIn(data)
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "done" and "aliasPr" not in state and github.opened == 1, state


def approval_holds():
    """#672: A approved, B entered after intake, restart: the alias and the data PR are A's."""
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data, fail_dispatch=1)
        go(root, github, data, photos)  # filed and merged for A, stopped before publishing
        write_job(root, itemId=OTHER)
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "done" and state["approval"]["itemId"] == ITEM, state
        assert github.dispatched[-1] == ("yourls-pilot.yml", {"item_ids": ITEM}), "the short link is A's"
        assert social_on(data, "main")[0]["shortAlias"] == "sdc25516ed66e0", "the alias PR records A's row"
    with TemporaryDirectory() as temp:  # main files the SPEC for B meanwhile: stop before the short link
        root, data, photos = setup(temp)
        github = StandIn(data, fail_dispatch=1)
        go(root, github, data, photos)
        recite(data, temp, [PRINTINGS[OTHER]])
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "alias" and "anderen Druck" in state["error"], state
        assert ("yourls-pilot.yml", {"item_ids": OTHER}) not in github.dispatched and len(github.dispatched) == 1


def source_first_printing():
    """main maps a SPEC of a source-first printing back by its source-first key, as intake cites it."""
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        write_job(root, itemId=SOURCE_FIRST)
        github = StandIn(data)
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "done", state
        assert github.dispatched[-1] == ("yourls-pilot.yml", {"item_ids": SOURCE_FIRST})
        assert social_on(data, "main")[1]["shortAlias"] == alias(SOURCE_FIRST)


def old_checkpoint():
    """A run from before the freeze resumes for the printing main filed its SPEC for, or stops."""
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data, fail_dispatch=1)
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        del state["approval"]
        runner.write_state(root / JOB, state)
        write_job(root, itemId=OTHER)
        go(root, github, data, photos)
        assert runner.read_state(root / JOB)["status"] == "done"
        assert github.dispatched[-1] == ("yourls-pilot.yml", {"item_ids": ITEM}), "main's printing, not the form's"
    with TemporaryDirectory() as temp:  # A's alias verified before #672, then main corrects the SPEC to C
        root, data, photos = setup(temp)
        github = StandIn(data, fail_dispatch=1)
        go(root, github, data, photos)  # filed and merged for A
        runner.write_state(root / JOB, {"status": "failed", "step": "alias-pr", "specimen": "SPEC-0001", "pr": 100,
                                        "done": ["intake", "merge", "publish", "alias"], "alias": alias(ITEM)})
        recite(data, temp, ["key-c"])
        go(root, github, data, photos)
        assert runner.read_state(root / JOB)["status"] == "done"
        assert github.dispatched == [("yourls-pilot.yml", {"item_ids": SOURCE_FIRST})], "verified again for C"
        rows = social_on(data, "main")
        assert rows[1]["shortAlias"] == alias(SOURCE_FIRST) and "shortAlias" not in rows[0], \
            "C's row gets C's own link, never the one that opens A"
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data, fail_dispatch=1)
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        del state["approval"]
        runner.write_state(root / JOB, state)
        recite(data, temp, [])  # ambiguous: main ties SPEC-0001 to no printing
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and "eindeutig" in state["error"] and len(github.dispatched) == 1, state


def own_run_only():
    """#673: GitHub's answer names the run; a foreign run of the same workflow decides nothing here."""
    with TemporaryDirectory() as temp:  # a Publish site started by hand succeeds while ours fails
        root, data, photos = setup(temp)
        github = StandIn(data)
        github.start_run("pages.yml", {})
        github.script["pages.yml"] = [(2, "failure")]
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "publish" and "failure" in state["error"], state
        assert state["publishRun"] == github.runs[1]["id"], "the failed dispatch, not the foreign success, stays visible"
        assert "pages.yml" not in state["runs"], "a run that clearly failed is dispatched anew"
        go(root, github, data, photos)
        retried = runner.read_state(root / JOB)
        assert retried["status"] == "done" and retried["publishRun"] == github.runs[2]["id"], retried
        assert [name for name, _ in github.dispatched] == ["pages.yml", "pages.yml", "yourls-pilot.yml"]
    with TemporaryDirectory() as temp:  # a foreign short-link run for the same printing succeeds, ours fails
        root, data, photos = setup(temp)
        github = StandIn(data)
        github.start_run("yourls-pilot.yml", {"item_ids": ITEM})
        github.script["yourls-pilot.yml"] = [(1, "failure")]
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "alias" and "alias" not in state, state
    with TemporaryDirectory() as temp:  # the run's result names another printing
        root, data, photos = setup(temp)
        github = StandIn(data)
        github.wrong_artifact = True
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and "nicht bestätigt" in state["error"] and "alias" not in state, state
        assert "yourls-pilot.yml" not in state["runs"] and "aliasPr" not in state, "the next start asks anew"


def one_dispatch():
    """#673: a new start waits for the run it dispatched. A lost answer is found by the run's title; it
    neither dispatches blindly again nor counts as success."""
    with TemporaryDirectory() as temp:  # A00 (#654): the inbox restarts while Publish site runs on to success
        root, data, photos = setup(temp)
        github = StandIn(data)
        github.script["pages.yml"], github.fail_poll = [(3, "success")], 1
        try:
            go(root, github, data, photos)
            raise AssertionError("the stand-in cuts the run off")
        except Crash:
            pass
        make(root, github, data, photos).recover()  # the restarted inbox marks the run interrupted
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and "Neustart" in state["error"] and state["step"] == "publish", state
        assert state["runs"]["pages.yml"]["runId"] == github.runs[0]["id"], "the run's id is beside the job"
        assert state["publishRun"] == github.runs[0]["id"], "the run can be opened before the first status poll"
        go(root, github, data, photos)  # "Erneut versuchen" waits for that run instead of a second one
        assert runner.read_state(root / JOB)["status"] == "done"
        assert [name for name, _ in github.dispatched] == ["pages.yml", "yourls-pilot.yml"], "Pages ran once"
    with TemporaryDirectory() as temp:  # GitHub started the run, its answer was lost, and the run fails
        root, data, photos = setup(temp)
        github = StandIn(data)
        github.lose_answer, github.script["pages.yml"] = 1, [(0, "failure")]
        try:
            go(root, github, data, photos)
            raise AssertionError("the stand-in cuts the run off")
        except Crash:
            pass
        state = runner.read_state(root / JOB)
        assert state["runs"]["pages.yml"]["runId"] is None, "the dispatch was on disk before GitHub heard of it"
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and "endete mit failure" in state["error"], state
        assert state["publishRun"] == github.runs[0]["id"], "a dispatch recovered by title also has its link"
        assert len(github.dispatched) == 1, "the lost run is found by its title, not dispatched again"
        go(root, github, data, photos)
        assert runner.read_state(root / JOB)["status"] == "done", "a run that clearly failed is dispatched anew"
    with TemporaryDirectory() as temp:  # the dispatch started nothing: no new one inside the grace
        root, data, photos = setup(temp)
        github = StandIn(data, fail_dispatch=1)
        go(root, github, data, photos)
        go(root, github, data, photos, grace=timedelta(minutes=10), patience=timedelta(0))
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and "ungeklärt" in state["error"] and github.dispatched == [], state
        go(root, github, data, photos)  # past the grace no run carries the token: dispatched anew
        assert runner.read_state(root / JOB)["status"] == "done"
    with TemporaryDirectory() as temp:  # an answer without the run's id, and GitHub lists the run late
        root, data, photos = setup(temp)
        github = StandIn(data)
        github.no_answer, github.lag = True, 2
        go(root, github, data, photos)
        state = runner.read_state(root / JOB)
        assert state["status"] == "done" and len(github.dispatched) == 2, state
        assert state["runs"]["pages.yml"]["runId"] == github.runs[0]["id"], state


def github_client():
    """The real client: the dispatch asks for the run's id and reads it from GitHub's answer; a run is
    found by its title only in a list GitHub gave in full."""
    calls, answers = [], iter([
        {"workflow_run_id": 42, "run_url": "https://api.github.com/r/42", "html_url": "https://github.com/r/42"},
        {"total_count": 2, "workflow_runs": [{"id": 7, "display_title": "Publish site inbox-x"},
                                             {"id": 8, "display_title": "Publish site "}]},
        {"total_count": 101, "workflow_runs": []}])
    client = runner.GitHub("token")
    client.call = lambda method, path, body=None: calls.append((method, path, body)) or next(answers)
    assert client.dispatch("pages.yml", {"request": "inbox-x"}) == 42
    assert calls[0] == ("POST", "/actions/workflows/pages.yml/dispatches",
                        {"ref": "main", "inputs": {"request": "inbox-x"}, "return_run_details": True}), calls
    assert client.runs_titled("pages.yml", "inbox-x", "2026-11-25T12:00:00+00:00") == [7]
    assert "created=%3E%3D2026-11-24T12%3A00%3A00Z" in calls[1][1], calls[1]
    assert client.runs_titled("pages.yml", "inbox-x", "2026-11-25T12:00:00+00:00") is None, "a cut list says nothing"


def required_checks():
    """#674: only the checks main's ruleset requires, at the head, by name and app, make a merge green."""
    client = runner.GitHub("token")
    client.call = lambda _method, _path, _body=None: [
        {"type": "pull_request", "parameters": {}},
        {"type": "required_status_checks", "parameters": {"required_status_checks": [
            {"context": "gate (ubuntu-latest)", "integration_id": 15368}, {"context": "gate (windows-latest)"}]}}]
    required = client.required_checks()
    assert required == [("gate (ubuntu-latest)", 15368), ("gate (windows-latest)", None)], required

    def run(name, conclusion="success", app=15368):
        return {"name": name, "status": "completed" if conclusion else "in_progress", "conclusion": conclusion,
                "app": {"id": app}}

    ubuntu, windows, side = "gate (ubuntu-latest)", "gate (windows-latest)", "ui"
    for runs, expected in (([], "pending"),
                           ([run(side)], "pending"),  # an early green side job stands in for nothing
                           ([run(side), run(ubuntu), run(windows, None)], "pending"),
                           ([run(ubuntu), run(windows), run(side, "skipped")], "success"),
                           ([run(ubuntu), run(windows, "skipped")], "success"),
                           ([run(ubuntu), run(windows, "cancelled")], "failure"),
                           ([run(ubuntu), run(windows, "neutral"), run(side, "failure")], "failure")):
        client.call = lambda _method, _path, _body=None, runs=runs: {"total_count": len(runs), "check_runs": runs}
        assert client.checks("abc", required) == expected, (runs, expected)
    client.call = lambda _method, _path, _body=None: {"total_count": 101, "check_runs": [run(ubuntu)]}
    assert client.checks("abc", [(ubuntu, 15368)]) == "pending", "a cut list proves nothing"
    client.call = lambda _method, _path, _body=None: {"total_count": 1, "check_runs": [run(ubuntu, app=1)]}
    assert client.checks("abc", [(ubuntu, 15368)]) == "pending", "the same name from another app is not the gate"


def corners_frozen():
    """Corners changed between the queue and intake do not replace the approval: intake never starts."""
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        write_job(root, corners=[[10, 10], [90, 10], [90, 140], [10, 140]])
        run = make(root, StandIn(data), data, photos)
        run.submit(JOB)
        write_job(root, corners=[[12, 10], [90, 10], [90, 140], [10, 140]])
        run.run(JOB)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "intake" and "Freigabe" in state["error"], state
        assert not Path(os.environ["FAKE_COUNT"]).exists(), "intake.py never ran"
        assert runner.assignment_lock(state) is None, "stopped before filing: the owner may correct it"
        go(root, StandIn(data), data, photos)  # "Erneut versuchen" freezes the corrected corners
        assert runner.read_state(root / JOB)["status"] == "done"


def run_record():
    """#685: a run records who queued it, when it started and ended; the night writes down its round."""
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        go(root, StandIn(data), data, photos)
        state = runner.read_state(root / JOB)
        assert state["origin"] == "button" and state["queuedAt"] <= state["startedAt"] <= state["finishedAt"], state
        assert runner.read_night(root) is None, "no round yet"
        run = make(root, StandIn(data), data, photos)
        run.night_round(lambda: [JOB])
        night, state = runner.read_night(root), runner.read_state(root / JOB)
        assert night["jobs"] == [JOB] and night["at"] and state["origin"] == "night", (night, state)
        assert state["status"] == "queued" and state["startedAt"] is None and state["finishedAt"] is None, state
        run.night_round(lambda: [JOB])  # still queued: the round queues nothing and says so
        assert runner.read_night(root)["jobs"] == []
        run.recover()
        assert runner.read_state(root / JOB)["finishedAt"], "a run a restart cut off has its end"


def recovers_and_queues_once():
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        runner.write_state(root / JOB, {"status": "running", "step": "merge", "done": ["intake"]})
        make(root, StandIn(data), data, photos).start()  # the restarted inbox; its queue stays empty
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and "Neustart" in state["error"] and state["done"] == ["intake"], state
        run = make(root, StandIn(data), data, photos)  # not started: the job stays queued
        assert run.submit(JOB) and not run.submit(JOB), "a queued job is not queued again"
        assert runner.read_state(root / JOB)["status"] == "queued"


def page_button():
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        plain = inbox.create_app(root).test_client()
        assert plain.get("/jobs").get_json()["intake"] is False
        assert plain.post(f"/jobs/{JOB}/intake").status_code == 503, "no runner, no intake"
        run = make(root, StandIn(data), data, photos)
        client = inbox.create_app(root, runner=run, schedule=False).test_client()
        listed = client.get("/jobs").get_json()
        assert listed["intake"] is True and listed["jobs"][0]["intake"]["blocked"], listed
        refused = client.post(f"/jobs/{JOB}/intake")
        assert refused.status_code == 409 and "Kartenecken" in refused.get_json()["error"], refused.get_json()
        blocked, inbox.intake_blocked = inbox.intake_blocked, lambda _folder, _filed: None
        try:
            started = client.post(f"/jobs/{JOB}/intake")
            assert started.status_code == 202 and started.get_json()["intake"]["run"]["status"] == "queued"
            assert client.post(f"/jobs/{JOB}/intake").status_code == 409, "a queued job is not started twice"
            assert inbox.ready_jobs(root, None) == [], "the night skips a queued job"
            assert client.delete(f"/jobs/{JOB}").status_code == 409, "a queued job stays out of the trash"
            runner.write_state(root / JOB, {"status": "failed", "error": "x", "done": []})
            assert inbox.ready_jobs(root, None) == [JOB], "the night tries a failed job again"
            # filed, but publishing failed: the catalogue names the SPEC, and the run still resumes
            inbox.intake_blocked = lambda _folder, _filed: "Schon übernommen als SPEC-0001."
            assert inbox.ready_jobs(root, None) == [], "a failed filing of a filed photo does not start again"
            runner.write_state(root / JOB, {"status": "failed", "step": "publish", "done": ["intake", "merge"]})
            assert client.get("/jobs").get_json()["jobs"][0]["intake"]["blocked"] is None
            assert inbox.ready_jobs(root, None) == [JOB], "the night finishes a filed job's run"
            assert client.post(f"/jobs/{JOB}/intake").status_code == 202, "the button finishes it too"
        finally:
            inbox.intake_blocked = blocked
        # D01: from "Übernehmen" on the printing and the corners stay as approved
        runner.write_state(root / JOB, {"status": "queued", "done": []})
        locked = client.get("/jobs").get_json()["jobs"][0]["intake"]["locked"]
        assert "SPEC-" not in locked and "läuft" in locked, locked
        refused = client.post(f"/jobs/{JOB}", json={"note": "Relaxo"})  # the form without A
        assert refused.status_code == 409 and refused.get_json()["error"] == locked
        assert client.post(f"/jobs/{JOB}/corners", json={}).status_code == 409, "no new corners either"
        runner.write_state(root / JOB, {"status": "failed", "step": "publish", "done": ["intake", "merge"],
                                        "specimen": "SPEC-0001"})
        assert "SPEC-0001" in client.post(f"/jobs/{JOB}", json={"note": "Relaxo"}).get_json()["error"], \
            "filed for A: locked for good, with the way to correct it"
        runner.write_state(root / JOB, {"status": "failed", "step": "intake", "done": []})
        described = client.post(f"/jobs/{JOB}", json={"note": "Relaxo"}).get_json()
        assert described["intake"] == client.get("/jobs").get_json()["jobs"][0]["intake"],             "a changed job answers with its intake state, so the page never shows a stale box"


def main():
    permalink_feedback()
    permalink_failure()
    permalink_local_gate()
    whole_chain()
    restart_after_failure()
    retry_after_failed_delivery()
    keeps_the_branch()
    worker_survives_a_trashed_job()
    red_ci_and_refusal()
    alias_already_recorded()
    further_evidence()
    approval_holds()
    source_first_printing()
    old_checkpoint()
    corners_frozen()
    own_run_only()
    one_dispatch()
    github_client()
    required_checks()
    recovers_and_queues_once()
    run_record()
    page_button()
    print("intake runner: all checks passed")


if __name__ == "__main__":
    main()
