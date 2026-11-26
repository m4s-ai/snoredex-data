"""The inbox's CI starts for the changes it tests and skips documentation (#677), and the image builds
the accepted tools (#681).

`.github/workflows/inbox-image.yml` builds the image and runs the inbox's suites; its `paths` filter
decides which pull requests start it. GitHub reads the patterns in order, a `!` pattern excludes what
the earlier ones matched, `*` stays inside one directory and `**` crosses them. The release gate has no
filter: it is the required check and must run on every pull request.

    python verification/test_inbox_ci.py
"""

import os
from pathlib import Path
import re
import sys

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"

STARTS = [
    "verification/photo_inbox/intake.py",           # intake
    "verification/photo_inbox/runner.py",           # the intake run
    "verification/photo_inbox/static/inbox.js",     # the page's JavaScript
    "verification/photo_inbox/templates/index.html",
    "verification/photo_inbox/docker/Dockerfile",   # the container
    "verification/photo_inbox/requirements.txt",
    "verification/photo_inbox/requirements.lock",   # what the image installs
    "verification/photo_inbox/test_app.py",         # the suites themselves
    "verification/instagram_package.py",            # the exporter
    "verification/test_instagram_package.py",
    "scripts/build.py",                             # imported by intake and the exporter
    "scripts/card_pages.py",
    "requirements.txt",                             # Playwright for test_app.py
    ".github/workflows/inbox-image.yml",            # the workflow itself
]
SKIPS = [
    "README.md",
    "verification/photo_inbox/README.md",            # documentation alone
    "verification/INSTAGRAM-PILOT.md",
    "data/social.json",                              # data: the release gate checks it
    ".github/workflows/release-gate.yml",
]


def pull_request_paths(workflow):
    """The `paths` list under `on: pull_request:`, or None when the trigger has none."""
    lines = (WORKFLOWS / workflow).read_text(encoding="utf-8").splitlines()
    start = lines.index("  pull_request:")
    paths, inside = [], False
    for line in lines[start + 1:]:
        if line and not line.startswith("    "):
            break  # the next trigger or key of `on`
        if line.strip() == "paths:":
            inside = True
        elif inside and line.strip().startswith("- "):
            paths.append(line.strip()[2:].strip("\"'"))
        elif inside and line.strip():
            inside = False
    return paths or None


def pattern(glob):
    out, i = "", 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif glob.startswith("**", i):
            out, i = out + ".*", i + 2
        elif glob[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif glob[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(glob[i]), i + 1
    return re.compile(out + r"\Z")


def starts(paths, changed):
    """Whether a pull request changing only `changed` starts the workflow."""
    def matched(path):
        hit = False
        for glob in paths:
            negative = glob.startswith("!")
            if pattern(glob.lstrip("!")).match(path):
                hit = not negative
        return hit
    return any(matched(path) for path in changed)


def toolchain_checks():
    """#681, D04: the Dockerfile builds what toolchain.json and requirements.lock record, and toolchain.py
    tells every difference of a running inbox from it."""
    inbox = Path(__file__).resolve().parent / "photo_inbox"
    sys.path.insert(0, str(inbox))
    import toolchain

    want = toolchain.accepted()
    dockerfile = (inbox / "docker" / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^FROM (\S+)$", dockerfile, re.M)[1] == want["base"], "the image builds FROM the accepted base"
    assert re.fullmatch(r"[^@\s]+@sha256:[0-9a-f]{64}", want["base"]), "the base is fixed by its digest"
    assert "pip install --no-cache-dir -r verification/photo_inbox/requirements.lock" in dockerfile
    pins = [line for line in toolchain.LOCK.read_text(encoding="utf-8").splitlines() if line and line[0] != "#"]
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.+-]*", pin) for pin in pins), pins
    chosen = [re.split(r"[<>=!~ ]", line)[0].lower() for line in
              (inbox / "requirements.txt").read_text(encoding="utf-8").splitlines() if line and line[0] != "#"]
    locked = {name.lower() for name in want["packages"]}
    assert set(chosen) <= locked, ("every chosen package is locked", set(chosen) - locked)

    have = {"python": want["python"], "tesseract": want["tesseract"], "languages": ["osd", *want["languages"]],
            "packages": dict(want["packages"])}
    assert toolchain.drift(want, have) == [], "the accepted tools match themselves"
    moved = dict(have, packages=dict(have["packages"], pillow="12.0.0"), languages=want["languages"][1:])
    assert toolchain.drift(want, moved) == [f"Tesseract-Sprache fehlt: {want['languages'][0]}",
                                            f"pillow: 12.0.0 statt {want['packages']['pillow']}"]
    configured = os.environ.get("TESSERACT")
    try:  # the check inspects the Tesseract the number guard runs: TESSERACT first, as number_check does
        os.environ["TESSERACT"] = str(Path(__file__).with_name("no-such-tesseract"))
        assert toolchain.binary() == os.environ["TESSERACT"] and toolchain.tesseract() == (None, [])
    finally:
        os.environ.pop("TESSERACT") if configured is None else os.environ.update(TESSERACT=configured)
    gone = dict(have, tesseract=None, languages=[], packages=dict(have["packages"], numpy=None))
    assert toolchain.drift(want, gone) == [f"tesseract: fehlt statt {want['tesseract']}",
                                           f"numpy: fehlt statt {want['packages']['numpy']}"]


def main():
    toolchain_checks()
    paths = pull_request_paths("inbox-image.yml")
    assert paths, "the inbox image workflow filters its pull requests"
    wrong = [p for p in STARTS if not starts(paths, [p])] + [p for p in SKIPS if starts(paths, [p])]
    assert not wrong, f"inbox-image.yml paths decide wrongly for: {wrong}"
    assert starts(paths, ["verification/photo_inbox/README.md", "verification/photo_inbox/app.py"]), \
        "documentation beside code still starts it"
    assert pattern("**/*.md").match("README.md") and not pattern("scripts/*").match("scripts/a/b.py")
    assert pull_request_paths("release-gate.yml") is None, "the required release gate runs on every pull request"
    print(f"inbox CI filter: {len(STARTS)} changes start it, {len(SKIPS)} do not; the release gate is unfiltered; "
          "the image builds the accepted tools")
    return 0


if __name__ == "__main__":
    sys.exit(main())
