"""A10: shared nightly deployment and durable alias groups, with local Git and a simulated GitHub."""
from io import BytesIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import zipfile

import runner
from test_runner import Crash, StandIn, alias, commit_on, git, remote, social_on

FAKE_INTAKE = '''import json, os, pathlib, subprocess, sys
data, photos, job = pathlib.Path.cwd(), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[1])
source = json.loads((job / "job.json").read_text())
n = source["number"]
spec = f"SPEC-{n:04d}"
count = pathlib.Path(os.environ["FAKE_COUNT"])
count.write_text(str(int(count.read_text()) + 1) if count.exists() else "1")
if source.get("refuse"):
    sys.exit("Synthetic refused intake")
photo = photos / (spec + ".jpg")
if not photo.exists():
    photo.write_bytes(b"photo" + str(n).encode())
    for args in (["add", "-A"], ["commit", "-q", "-m", spec], ["push", "-q"]):
        subprocess.run(["git", "-C", str(photos), *args], check=True)
subprocess.run(["git", "switch", "-q", "-c", "intake/" + spec, "origin/main"], check=True)
path = data / "verification/specimens.json"
records = json.loads(path.read_text())
records["specimens"].append({"specimenId": spec, "photographedBy": "collection owner", "citedBy": ["printing-" + str(n)]})
path.write_text(json.dumps(records))
path = data / "data/social.json"
rows = json.loads(path.read_text())
row = {"itemId": source["itemId"], "specimenId": spec, "instagramPosts": []}
if source.get("alias"):
    row["shortAlias"] = source["alias"]
rows.append(row)
path.write_text(json.dumps(rows, indent=2) + "\\n")
(data / "index.html").write_text(spec + "\\n")
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-q", "-m", "File " + spec], check=True)
pathlib.Path(sys.argv[sys.argv.index("--result") + 1]).write_text(json.dumps(
    {"branch": "intake/" + spec, "specimen": spec, "itemId": source["itemId"], "keeps": None}))
'''


class GitHub(StandIn):
    def __init__(self, data):
        super().__init__(data)
        self.bad, self.published, self.artifact_reads = set(), [], []

    def dispatch(self, workflow, inputs):
        if workflow == "pages.yml":
            self.published = social_on(self.remote, "main")
        run_id = super().dispatch(workflow, inputs)
        if workflow == "yourls-pilot.yml" and self.bad.intersection(inputs["item_ids"].split()):
            self.runs[-1]["conclusion"] = "failure"
        return run_id

    def start_run(self, workflow, inputs, *args):
        run = super().start_run(workflow, inputs, *args)
        run["head_sha"] = git("--git-dir", self.remote, "rev-parse", "main")
        return run

    def artifact(self, run_id, name):
        assert name == "yourls-verified"
        self.artifact_reads.append(run_id)
        run = next(run for run in self.runs if run["id"] == run_id)
        rows = [{"itemId": item, "shortAlias": alias(item), "status": "failed" if item in self.bad else "verified",
                 "shortUrl": "https://go.m4s.eu/" + alias(item), "redirectStatus": 302,
                 "targetUrl": "https://m4s-ai.github.io/snoredex-data/cards/" + item + "/"}
                for item in run["inputs"]["item_ids"].split()]
        if self.wrong_artifact:
            rows[0]["itemId"] = "item-ffffffff-ffff-5fff-8fff-ffffffffffff"
        out = BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            archive.writestr("yourls-result.json", json.dumps(rows[0] if len(rows) == 1 else rows))
        return out.getvalue()


def setup(temp, count=10, existing=()):
    items = [f"item-{n:08x}-1111-5111-8111-{n:012x}" for n in range(1, count + 1)]
    catalogue = {"meta": {"assetBaseUrl": "https://example.invalid/", "dataAsOf": "2026-11-26"},
                 "localizations": [{"localizationId": "en", "displayName": "English"}], "assets": [],
                 "items": [{"itemId": item, "active": True, "localizationId": "en", "cardName": "Snorlax",
                            "sourcePrintingId": f"printing-{n}", "sourceClaimRefs": []}
                           for n, item in enumerate(items, 1)]}
    data = remote(temp, "data", {"verification/photo_inbox/intake.py": FAKE_INTAKE, "scripts/regen.py": "",
                                 "verification/publication_audit.py": "", "data/social.json": "[]\n",
                                 "collector_catalogue.json": json.dumps(catalogue),
                                 "verification/specimens.json": json.dumps({"specimens": []}),
                                 "data/images.json": json.dumps({"galleryImages": []})})
    photos = remote(temp, "photos", {"README.md": "archive\n"})
    root = Path(temp) / "inbox"
    jobs = []
    for n, item in enumerate(items, 1):
        job = f"{n:064x}"
        (root / job).mkdir(parents=True)
        (root / job / "job.json").write_text(json.dumps({"id": job, "number": n, "file": "photo.jpg",
            "itemId": item, **({"alias": alias(item)} if n in existing else {})}), encoding="utf-8", newline="\n")
        jobs.append(job)
    os.environ["FAKE_COUNT"] = str(Path(temp) / "intake-count")
    return root, data, photos, jobs, items


def make(root, github, data, photos):
    run = runner.Runner(root, github, urls=(data, photos), poll=0, sleep=lambda _: None)

    def verify(items):
        remote = {row["itemId"]: row for row in github.published}
        local = {row["itemId"]: row for row in json.loads((run.data / "data/social.json").read_text())}
        if not all(remote.get(item) == local.get(item) for item in items):
            raise runner.RunError("Public rows do not reconcile against main")

    run.verify_publication = verify
    return run


def dispatched(github, name):
    return [inputs for workflow, inputs in github.dispatched if workflow == name]


def ten_photos():
    with TemporaryDirectory() as temp:
        root, data, photos, jobs, items = setup(temp)
        github = GitHub(data)
        run = make(root, github, data, photos)
        run.night_round(lambda: jobs)
        assert run.jobs.qsize() == 1, "one durable nightly batch, not ten full individual runs"
        run.process_next(timeout=0)
        states = [runner.read_state(root / job) for job in jobs]
        assert all(state["status"] == "done" for state in states), states
        assert len(dispatched(github, "pages.yml")) == 1
        groups = dispatched(github, "yourls-pilot.yml")
        assert [len(group["item_ids"].split()) for group in groups] == [3, 3, 3, 1]
        assert [item for group in groups for item in group["item_ids"].split()] == items
        assert len({state["aliasPr"] for state in states}) == 1 and github.opened == 11
        assert len({state["publishRun"] for state in states}) == 1 and all(state["aliasRun"] for state in states)
        assert Path(os.environ["FAKE_COUNT"]).read_text() == "10"
        assert all(row["shortAlias"] == alias(row["itemId"]) for row in social_on(data, "main"))
        # D06: the data PR is not followed by an immediate second deploy. The next round flushes it.
        run.night_round(lambda: [])
        run.process_next(timeout=0)
        assert len(dispatched(github, "pages.yml")) == 2 and len(dispatched(github, "yourls-pilot.yml")) == 4
        assert github.opened == 11
        run.night_round(lambda: [])
        assert run.jobs.empty(), "nothing pending: no further deploy"


def partial_and_restart():
    with TemporaryDirectory() as temp:
        root, data, photos, jobs, items = setup(temp, count=3)
        github = GitHub(data)
        github.bad = {items[1]}
        run = make(root, github, data, photos)
        run.night_round(lambda: jobs)
        run.process_next(timeout=0)
        states = [runner.read_state(root / job) for job in jobs]
        assert states[0]["alias"] == alias(items[0]) and states[2]["alias"] == alias(items[2]), states
        assert all(state["status"] == "failed" for state in states)
        assert all(state["step"] == "alias" for state in states), "the report names the actual failed phase"
        assert github.opened == 3 and len(dispatched(github, "yourls-pilot.yml")) == 1
        github.bad.clear()
        run = make(root, github, data, photos)
        run.recover()
        assert run.submit(jobs[1]) and not run.submit(jobs[0]), "a retry queues the owning batch exactly once"
        run.process_next(timeout=0)
        assert all(runner.read_state(root / job)["status"] == "done" for job in jobs)
        assert dispatched(github, "yourls-pilot.yml")[-1]["item_ids"] == items[1], "only the failed item is retried"
        assert len(dispatched(github, "pages.yml")) == 1 and github.opened == 4
        assert Path(os.environ["FAKE_COUNT"]).read_text() == "3"


def reused_and_button():
    with TemporaryDirectory() as temp:
        root, data, photos, jobs, items = setup(temp, count=3, existing=(1, 3))
        github = GitHub(data)
        run = make(root, github, data, photos)
        run.night_round(lambda: jobs)
        run.process_next(timeout=0)
        assert dispatched(github, "yourls-pilot.yml") == [{"item_ids": items[1]}]
        assert runner.read_state(root / jobs[0])["aliasReused"]
        assert runner.read_state(root / jobs[2])["aliasReused"]
    with TemporaryDirectory() as temp:
        root, data, photos, jobs, _items = setup(temp, count=1)
        github = GitHub(data)
        run = make(root, github, data, photos)
        assert run.submit(jobs[0])
        run.process_next(timeout=0)
        assert runner.read_state(root / jobs[0])["status"] == "done", runner.read_state(root / jobs[0])
        assert len(dispatched(github, "pages.yml")) == len(dispatched(github, "yourls-pilot.yml")) == 1


def interrupted_dispatch_and_results():
    for phase in ("dispatch", "results"):
        with TemporaryDirectory() as temp:
            root, data, photos, jobs, _items = setup(temp, count=2)
            github = GitHub(data)
            run = make(root, github, data, photos)
            run.night_round(lambda: jobs)
            if phase == "dispatch":
                github.lose_answer = 1
            write, crashed = runner.write_state, []

            def stopped(folder, state):
                write(folder, state)
                if phase == "results" and folder == root / jobs[0] and state.get("alias") and not crashed:
                    crashed.append(True)
                    raise Crash

            with patch("runner.write_state", side_effect=stopped):
                try:
                    run.process_next(timeout=0)
                except Crash:
                    pass
                else:
                    raise AssertionError("the inbox died at the persistence boundary")
            run = make(root, github, data, photos)
            run.recover()
            run.submit(jobs[0])
            run.process_next(timeout=0)
            assert all(runner.read_state(root / job)["status"] == "done" for job in jobs)
            assert len(dispatched(github, "pages.yml")) == len(dispatched(github, "yourls-pilot.yml")) == 1
            assert github.opened == 3 and Path(os.environ["FAKE_COUNT"]).read_text() == "2"


def wrong_artifact_and_foreign_branch():
    with TemporaryDirectory() as temp:
        root, data, photos, jobs, _items = setup(temp, count=2)
        github = GitHub(data)
        github.wrong_artifact = True
        run = make(root, github, data, photos)
        run.night_round(lambda: jobs)
        run.process_next(timeout=0)
        assert all("shortAlias" not in row for row in social_on(data, "main")), "foreign artifact writes no assignment"
        assert all(runner.read_state(root / job)["status"] == "failed" for job in jobs)
        github.wrong_artifact = False
        run.submit(jobs[0])
        run.process_next(timeout=0)
        assert all(runner.read_state(root / job)["status"] == "done" for job in jobs)
    with TemporaryDirectory() as temp:
        root, data, photos, jobs, _items = setup(temp, count=1)
        github = GitHub(data)
        open_pull = github.open_pull

        def reject_alias(branch, title, body):
            if branch.endswith("-aliases"):
                raise runner.RunError("Synthetic lost PR-open response")
            return open_pull(branch, title, body)

        github.open_pull = reject_alias
        run = make(root, github, data, photos)
        run.night_round(lambda: jobs)
        run.process_next(timeout=0)
        import night_batch
        batch = runner.read_state(root / jobs[0])["batch"]
        branch = runner.read_state(night_batch.folder(run, batch))["branch"]
        foreign = commit_on(data, temp, branch)
        github.open_pull = open_pull
        run.submit(jobs[0])
        run.process_next(timeout=0)
        state = runner.read_state(root / jobs[0])
        assert state["status"] == "failed" and "fremden Stand" in state["error"], state
        assert git("--git-dir", data, "rev-parse", branch) == foreign


def refused_and_public_check():
    with TemporaryDirectory() as temp:
        root, data, photos, jobs, _items = setup(temp, count=2)
        path = root / jobs[0] / "job.json"
        job = json.loads(path.read_text())
        path.write_text(json.dumps(dict(job, refuse=True)), encoding="utf-8", newline="\n")
        github = GitHub(data)
        run = make(root, github, data, photos)
        run.night_round(lambda: jobs)
        run.process_next(timeout=0)
        assert runner.read_state(root / jobs[0])["batchExcluded"]
        assert runner.read_state(root / jobs[1])["status"] == "done", "a refused intake does not stop its neighbour"
    with TemporaryDirectory() as temp:
        root, data, photos, jobs, _items = setup(temp, count=1)
        github = GitHub(data)
        run = make(root, github, data, photos)
        verify = run.verify_publication
        run.verify_publication = lambda _items: (_ for _ in ()).throw(runner.RunError("Public check unavailable"))
        run.night_round(lambda: jobs)
        run.process_next(timeout=0)
        assert runner.read_state(root / jobs[0])["status"] == "failed"
        run.verify_publication = verify
        run.submit(jobs[0])
        run.process_next(timeout=0)
        assert runner.read_state(root / jobs[0])["status"] == "done"
        assert len(dispatched(github, "pages.yml")) == 1, "a public-check retry follows the completed deployment"


def public_reconciliation():
    import night_batch
    with TemporaryDirectory() as temp:
        repo = Path(temp)
        (repo / "data").mkdir()
        item = "item-11111111-1111-5111-8111-111111111111"
        row = {"itemId": item, "specimenId": "SPEC-0001", "shortAlias": "sdtest", "instagramPosts": [],
               "threadsPosts": ["https://www.threads.com/@snoredex/post/abc"]}
        (repo / "data/social.json").write_text(json.dumps([row]), encoding="utf-8", newline="\n")
        with (patch("night_batch.request", return_value=json.dumps([row]).encode()),
              patch("night_batch.card_plan", return_value=({"itemId": item}, "preview.png")) as plan,
              patch("night_batch.verify_public_page") as page, patch("night_batch.verify_redirect") as redirect):
            night_batch.verify_publication(repo, [item])
            plan.assert_called_once_with(item, None, repo)
            page.assert_called_once_with({"itemId": item}, "preview.png", repo)
            redirect.assert_called_once()
        with patch("night_batch.request", return_value=json.dumps([dict(row, threadsPosts=[])]).encode()):
            try:
                night_batch.verify_publication(repo, [item])
            except runner.RunError:
                pass
            else:
                raise AssertionError("a missing published backlink must not pass reconciliation")


def empty_publication_retry():
    with TemporaryDirectory() as temp:
        root, data, photos, jobs, items = setup(temp, count=1)
        github = GitHub(data)
        run = make(root, github, data, photos)
        run.night_round(lambda: jobs)
        run.process_next(timeout=0)
        run.verify_publication = lambda _items: (_ for _ in ()).throw(runner.RunError("Read failed"))
        run.night_round(lambda: [])
        run.process_next(timeout=0)
        assert len(dispatched(github, "pages.yml")) == 2
        order = root / ".posts/SPEC-0001/order.json"
        order.parent.mkdir(parents=True)
        order.write_text(json.dumps({"itemId": items[0], "targets": {
            "ig:snoredex": {"status": "published", "permalink": "https://www.instagram.com/p/later/"}
        }}), encoding="utf-8", newline="\n")
        run.record_posts()
        assert social_on(data, "main")[0]["instagramPosts"], "the same pending item changed after deployment"
        run = make(root, github, data, photos)
        run.night_round(lambda: [])
        run.process_next(timeout=0)
        assert len(dispatched(github, "pages.yml")) == 2, "a pending-only retry follows its saved deployment"
        run.night_round(lambda: [])
        assert run.jobs.qsize() == 1, "the newer permalink remains pending"
        run.process_next(timeout=0)
        assert len(dispatched(github, "pages.yml")) == 3
        assert github.published[0]["instagramPosts"] == ["https://www.instagram.com/p/later/"]
        run.night_round(lambda: [])
        assert run.jobs.empty()


def main():
    ten_photos()
    partial_and_restart()
    reused_and_button()
    interrupted_dispatch_and_results()
    wrong_artifact_and_foreign_branch()
    refused_and_public_check()
    public_reconciliation()
    empty_publication_retry()
    print("night batch: all checks passed")


if __name__ == "__main__":
    main()
