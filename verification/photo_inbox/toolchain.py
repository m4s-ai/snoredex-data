"""Whether the running inbox has the tools it was accepted with (#681, owner decision D04).

The image is built locally from a base image fixed by its digest, with every package at the version
requirements.lock names. toolchain.json records the rest of the accepted state: the Python version that
base carries, Tesseract's version and the collection's languages. This compares what runs with both; the
inbox reports the result in /version and its version line, and the operator can run it in the container:

    docker compose exec inbox python verification/photo_inbox/toolchain.py --check

Debian's packages (Tesseract) follow bookworm's updates and are not pinned; a moved version shows here.
"""

from importlib import metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASELINE, LOCK = HERE / "toolchain.json", HERE / "requirements.lock"


def accepted():
    """The accepted state: toolchain.json plus each package requirements.lock pins."""
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    pins = [line.split("==") for line in LOCK.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]
    return dict(baseline, packages={name: version for name, version in pins})


def tesseract():
    """Tesseract's version and languages, or (None, []) when it cannot be run."""
    try:
        version = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=10)
        langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None, []
    found = re.search(r"tesseract v?([0-9][0-9.]*)", version.stdout + version.stderr)
    return (found[1] if found else None), langs.stdout.split()[1:]  # the first line is a heading


def running():
    """The tools this process has now."""
    packages = {}
    for name in accepted()["packages"]:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    version, languages = tesseract()
    return {"python": platform.python_version(), "tesseract": version, "languages": languages, "packages": packages}


def drift(want, have):
    """Every way `have` differs from the accepted `want`, as lines a person reads; empty when it matches."""
    out = [f"{key}: {have[key] or 'fehlt'} statt {want[key]}" for key in ("python", "tesseract") if have[key] != want[key]]
    out += [f"Tesseract-Sprache fehlt: {lang}" for lang in want["languages"]
            if have["tesseract"] and lang not in have["languages"]]  # without Tesseract, one line says it
    out += [f"{name}: {have['packages'].get(name) or 'fehlt'} statt {version}"
            for name, version in want["packages"].items() if have["packages"].get(name) != version]
    return out


def report():
    """What /version says: whether the tools match, and how they differ."""
    found = drift(accepted(), running())
    return {"matches": not found, "drift": found}


def main(argv=None):
    check = "--check" in (sys.argv[1:] if argv is None else argv)
    found = report()
    print("Werkzeugstand wie abgenommen." if found["matches"] else "Werkzeugstand weicht ab:\n- " +
          "\n- ".join(found["drift"]))
    return 1 if check and not found["matches"] else 0


if __name__ == "__main__":
    sys.exit(main())
