#!/usr/bin/env python3
"""Offline checks for the issue-image importer."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "verification"))
from fetch_attachment import issue_attachments  # noqa: E402


def main() -> None:
    html = """
    <a href="https://github.com/user-attachments/assets/stable-a">
      <img src="https://private-user-images.githubusercontent.com/1/signed-a.png">
    </a>
    <a href="https://github.com/user-attachments/assets/stable-b">
      <img src="https://github.com/user-attachments/assets/stable-b">
    </a>
    """
    assert issue_attachments(html) == [
        (
            "https://github.com/user-attachments/assets/stable-a",
            [
                "https://github.com/user-attachments/assets/stable-a",
                "https://private-user-images.githubusercontent.com/1/signed-a.png",
            ],
        ),
        (
            "https://github.com/user-attachments/assets/stable-b",
            ["https://github.com/user-attachments/assets/stable-b"],
        ),
    ]
    print("fetch_attachment issue parser regression passed")


if __name__ == "__main__":
    main()
