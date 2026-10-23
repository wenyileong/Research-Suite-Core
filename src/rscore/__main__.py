"""Command line for the shared core: ``python -m rscore <command>``.

Commands:
  import-ashare RELEASE_DIR   import an A-share Company Intelligence release into a project store
  export-lab                  write the store's Lab tables as a dataset the Lab can import
  snapshot                    export a hashed, verifiable snapshot of the store
  validate                    re-check the whole store
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rscore import export, snapshot
from rscore.importers import ashare
from rscore.store import Store
from rscore.validation import ValidationError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m rscore", description="Research Suite shared core")
    p.add_argument("--store", type=Path, default=Path("project.sqlite"), help="project store (default project.sqlite)")
    sub = p.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import-ashare", help="import an A-share Company Intelligence release")
    imp.add_argument("release", type=Path, help="release folder (holds manifest.json and csv/)")
    imp.add_argument("--company", action="append", default=[], metavar="CODE",
                     help="import only this security code (repeatable), e.g. --company 000563")
    imp.add_argument("--overrides", type=Path, help="filled-in review_jurisdictions.csv (name, jurisdiction_id)")
    imp.add_argument("--accept-suggestions", action="store_true",
                     help="accept jurisdictions suggested from holder names without review")
    imp.add_argument("--assume-consolidated", action="store_true",
                     help="treat revenue with no stated consolidation scope as consolidated")
    imp.add_argument("--min-confidence", type=float, default=0.0, help="reject rows below this extraction confidence")
    imp.add_argument("--report", type=Path, default=Path("import_report"), help="folder for the report files")

    lab = sub.add_parser("export-lab", help="write a dataset for the International Tax Network Lab")
    lab.add_argument("out", type=Path)
    snap = sub.add_parser("snapshot", help="export a verifiable snapshot")
    snap.add_argument("out", type=Path)
    snap.add_argument("--note")
    sub.add_parser("validate", help="re-check the whole store")

    args = p.parse_args(argv)
    try:
        with Store(args.store) as store:
            if args.command == "import-ashare":
                opts = ashare.Options(
                    companies=tuple(args.company),
                    overrides=ashare.read_overrides(args.overrides) if args.overrides else {},
                    accept_suggestions=args.accept_suggestions, assume_consolidated=args.assume_consolidated,
                    min_confidence=args.min_confidence)
                report = ashare.import_release(store, args.release, opts)
                ashare.write_report(report, args.report)
                print((args.report / "import_report.md").read_text(encoding="utf-8"))
            elif args.command == "export-lab":
                for path in export.lab_dataset(store, args.out):
                    print(path)
            elif args.command == "snapshot":
                print(snapshot.export(store, args.out, note=args.note))
            elif args.command == "validate":
                report = store.validate()
                print(report)
                return 0 if report.ok else 1
    except ValidationError as exc:
        print(f"Validation failed; nothing was written for the failing table:\n{exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
