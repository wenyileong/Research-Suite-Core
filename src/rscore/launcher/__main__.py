"""Entry point: ``python -m rscore.launcher`` (and the Windows executable)."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from rscore import __version__


def _say(message: str) -> None:
    # A windowed executable has no console, so sys.stdout is None there.
    if sys.stdout is not None:
        print(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ResearchSuite", description="Research Suite launcher")
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    parser.add_argument("--self-test", action="store_true", help="build the window once, then exit")
    parser.add_argument("--config", type=Path, help="settings file to use instead of the default")
    args = parser.parse_args(argv)
    if args.version:
        _say(__version__)
        return 0
    from rscore.launcher import app

    if args.self_test:
        with tempfile.TemporaryDirectory() as tmp:
            app.self_test(Path(tmp) / "launcher.json")
        _say("self-test ok")
        return 0
    app.run(args.config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
