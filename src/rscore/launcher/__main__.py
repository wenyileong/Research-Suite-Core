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
    parser.add_argument("--log", type=Path, help="with --self-test: write the outcome (and any error) to this file")
    args = parser.parse_args(argv)
    if args.version:
        _say(__version__)
        return 0
    from rscore.launcher import app

    if args.self_test:
        # Errors are reported as text and an exit code, never as a dialog: a windowed executable would
        # otherwise wait for someone to close the error box.
        import traceback
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                app.self_test(Path(tmp) / "launcher.json")
        except Exception:
            message = "self-test FAILED\n" + traceback.format_exc()
            code = 1
        else:
            message, code = "self-test ok", 0
        _say(message)
        if args.log:
            args.log.write_text(message + "\n", encoding="utf-8")
        return code
    app.run(args.config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
