"""Check formatting of Python files changed by a pull request or push."""

import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    base = os.environ.get("FORMAT_BASE", "HEAD")
    if not base or set(base) == {"0"}:
        base = (
            subprocess.check_output(
                ["git", "hash-object", "-t", "tree", "--stdin"], input=b""
            )
            .decode()
            .strip()
        )
    changed = (
        subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "-z", base, "HEAD"]
        )
        .decode()
        .split("\0")
    )
    files = [name for name in changed if name.endswith(".py") and Path(name).is_file()]
    if not files:
        print("No changed Python files to check.")
        return 0
    return subprocess.call([sys.executable, "-m", "ruff", "format", "--diff", *files])


if __name__ == "__main__":
    raise SystemExit(main())
