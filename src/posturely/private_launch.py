"""macOS launcher that denies all Posturely network access at the OS boundary."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence

_SANDBOX_PROFILE = "(version 1)\n(allow default)\n(deny network*)"


def build_private_command(
    argv: Sequence[str],
    *,
    python: str = sys.executable,
) -> list[str]:
    return [
        "/usr/bin/sandbox-exec",
        "-p",
        _SANDBOX_PROFILE,
        python,
        "-m",
        "posturely",
        *argv,
    ]


def main(argv: Sequence[str] | None = None) -> int:
    command = build_private_command(sys.argv[1:] if argv is None else argv)
    os.execv(command[0], command)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
