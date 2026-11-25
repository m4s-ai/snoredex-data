"""The intake run without an agent (#659), against local Git remotes and a stand-in GitHub.

The real intake.py, check.py and regen.py are tested on their own (test_intake.py); here a stand-in
intake.py in the remote does what the run relies on: push the archive copy, commit on intake/SPEC-nnnn,
print the branch, or refuse with a reason. Checked: the whole chain, a restart after every failure
without a second intake, pull request or merge, red CI, a refusal, an alias already on main, a run a
restart cut off, and the page's button.

    python verification/photo_inbox/test_runner.py
"""

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
JOB = "a" * 64
FAKE_INTAKE = '''import os, pathlib, subprocess, sys
data, photos = pathlib.Path.cwd(), pathlib.Path(sys.argv[3])
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
(data / "filed.txt").write_text("SPEC-0001\\n")
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-q", "-m", "File SPEC-0001"], check=True)
print("intake/SPEC-0001")
'''


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
        return dict(pull, head={"sha": git("--git-dir", self.remote, "rev-parse", pull["branch"])})

    def checks(self, _sha):
        return self.result

    def merge(self, number, sha):
        pull = self.pulls[number]
        assert sha == git("--git-dir", self.remote, "rev-parse", pull["branch"]), "merged at the checked head"
        git("--git-dir", self.remote, "update-ref", "refs/heads/main", sha)  # fast-forward: the branch is on main
        pull.update(merged_at="2026-11-25T12:00:00Z", state="closed")
        self.merged.append(number)

    def dispatch(self, workflow, inputs):
        if self.fail_dispatch:
            self.fail_dispatch -= 1
            raise runner.RunError(f"GitHub POST {workflow}: 500")
        self.dispatched.append((workflow, inputs))

    def run_since(self, workflow, _since):
        return {"id": len(self.dispatched), "status": "completed", "conclusion": "success",
                "html_url": f"https://example.invalid/{workflow}"}

    def artifact(self, _run_id, name):
        assert name == "yourls-verified"
        out = BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            archive.writestr("yourls-result.json", json.dumps(
                {"itemId": ITEM, "shortAlias": "sdc25516ed66e0", "status": "verified"}))
        return out.getvalue()


def setup(temp, alias=None):
    social = [{"itemId": ITEM, "specimenId": "SPEC-0001", "instagramPosts": [],
               **({"shortAlias": alias} if alias else {})}]
    data = remote(temp, "data", {"verification/photo_inbox/intake.py": FAKE_INTAKE, "scripts/regen.py": "",
                                 "data/social.json": json.dumps(social, indent=2) + "\n"})
    photos = remote(temp, "photos", {"README.md": "archive\n"})
    root = Path(temp) / "inbox"
    (root / JOB).mkdir(parents=True)
    (root / JOB / "job.json").write_text(json.dumps({"id": JOB, "itemId": ITEM, "file": "photo.dng"}), encoding="utf-8",
                                       newline="\n")
    os.environ["FAKE_COUNT"] = str(Path(temp) / "intake-count")
    return root, data, photos


def make(root, github, data, photos):
    return runner.Runner(root, github, urls=(data, photos), sleep=lambda _seconds: None, poll=0)


def social_on(data_remote, ref):
    return json.loads(git("--git-dir", data_remote, "show", f"{ref}:data/social.json"))


def whole_chain():
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data)
        make(root, github, data, photos).run(JOB)
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
        make(root, github, data, photos).run(JOB)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "publish" and "500" in state["error"], state
        make(root, github, data, photos).run(JOB)
        assert runner.read_state(root / JOB)["status"] == "done"
        assert Path(os.environ["FAKE_COUNT"]).read_text() == "1", "the photo is filed once"
        assert github.opened == 2 and len(github.merged) == 2, "no pull request opened or merged twice"


def retry_after_failed_delivery():
    """The filing committed but its pull request did not open: the retry files again in the same clones."""
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        github = StandIn(data, fail_open=1)
        make(root, github, data, photos).run(JOB)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "intake" and "502" in state["error"], state
        make(root, github, data, photos).run(JOB)
        assert runner.read_state(root / JOB)["status"] == "done", runner.read_state(root / JOB)
        assert git("--git-dir", photos, "rev-list", "--count", "main") == "2", "one archive copy, reused"


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
        make(root, StandIn(data, checks="failure"), data, photos).run(JOB)
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and state["step"] == "merge" and "ist rot" in state["error"], state
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp)
        os.environ["FAKE_REFUSE"] = "1"
        try:
            make(root, StandIn(data), data, photos).run(JOB)
        finally:
            del os.environ["FAKE_REFUSE"]
        state = runner.read_state(root / JOB)
        assert state["status"] == "failed" and "Kartenecken" in state["error"], state


def alias_already_recorded():
    with TemporaryDirectory() as temp:
        root, data, photos = setup(temp, alias="sdc25516ed66e0")
        github = StandIn(data)
        make(root, github, data, photos).run(JOB)
        state = runner.read_state(root / JOB)
        assert state["status"] == "done" and "aliasPr" not in state and github.opened == 1, state


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
        described = client.post(f"/jobs/{JOB}", json={"note": "Relaxo"}).get_json()
        assert described["intake"] == client.get("/jobs").get_json()["jobs"][0]["intake"],             "a changed job answers with its intake state, so the page never shows a stale box"


def main():
    whole_chain()
    restart_after_failure()
    retry_after_failed_delivery()
    worker_survives_a_trashed_job()
    red_ci_and_refusal()
    alias_already_recorded()
    recovers_and_queues_once()
    page_button()
    print("intake runner: all checks passed")


if __name__ == "__main__":
    main()
