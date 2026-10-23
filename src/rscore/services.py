"""Everything the suite can do, as plain functions shared by the command line and the window.

Rule for future work (see ``docs/interface_guidelines.md``): a new capability is added here first, then
exposed both as a command in ``rscore.__main__`` and as an action in the window. A test checks that
every command has a window action.

A project is one SQLite store file. Beside it the services keep a folder ``<name>_files`` holding import
reports, the jurisdiction overrides chosen during review, Lab exports and snapshots, so that everything
belonging to a project travels with it.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from rscore import export, jurisdictions, places, snapshot
from rscore import schema as sc
from rscore.importers import ashare
from rscore.store import Store
from rscore.validation import Report

#: What the window must offer for each command (checked by a test).
COMMANDS = ("import-ashare", "export-lab", "snapshot", "validate")

OVERRIDES_FILE = "jurisdiction_overrides.csv"


# ------------------------------------------------------------------ projects
@dataclass(frozen=True)
class Project:
    path: Path

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def files(self) -> Path:
        folder = self.path.with_name(self.path.stem + "_files")
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    @property
    def overrides_path(self) -> Path:
        return self.files / OVERRIDES_FILE

    def open(self) -> Store:
        return Store(self.path)


def create_project(path: str | Path) -> Project:
    """Create (or open) a project store, seeded with the jurisdiction registry and place aliases."""
    path = Path(path)
    if path.suffix.lower() not in (".sqlite", ".db"):
        path = path.with_suffix(".sqlite")
    path.parent.mkdir(parents=True, exist_ok=True)
    with Store(path) as store:
        jurisdictions.seed(store)
        places.seed_aliases(store)
    return Project(path)


#: Tables shown in the project summary, in reading order.
SUMMARY_TABLES = ("entities", "ownership", "entity_financials", "sources", "jurisdictions", "instruments",
                  "provisions", "regime_values", "authorities", "propositions")


def summary(project: Project) -> dict[str, int]:
    with project.open() as store:
        return {t: store.count(t) for t in SUMMARY_TABLES}


# ------------------------------------------------------------------ import
@dataclass
class ImportResult:
    report: ashare.ImportReport
    report_dir: Path


def run_import(project: Project, release: str | Path, *, companies: tuple[str, ...] = (),
               assume_consolidated: bool = False, accept_suggestions: bool = False, min_confidence: float = 0.0,
               progress: Callable[[str], None] | None = None) -> ImportResult:
    """Import a release, using the project's saved overrides, and write the report files into the project."""
    say = progress or (lambda _m: None)
    say("reading")
    overrides = load_overrides(project)
    opts = ashare.Options(companies=companies, overrides=overrides, accept_suggestions=accept_suggestions,
                          assume_consolidated=assume_consolidated, min_confidence=min_confidence)
    with project.open() as store:
        say("importing")
        report = ashare.import_release(store, release, opts)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    report_dir = project.files / "import_reports" / f"{report.release}_{stamp}"
    say("writing report")
    ashare.write_report(report, report_dir)
    (report_dir / "settings.json").write_text(json.dumps({
        "release_folder": str(Path(release).resolve()), "companies": list(companies),
        "assume_consolidated": assume_consolidated, "accept_suggestions": accept_suggestions,
        "min_confidence": min_confidence, "overrides_used": len(overrides)}, indent=2) + "\n", encoding="utf-8")
    return ImportResult(report, report_dir)


def latest_report(project: Project) -> Path | None:
    folder = project.files / "import_reports"
    reports = sorted((p for p in folder.glob("*") if (p / "import_report.json").exists()),
                     key=lambda p: p.stat().st_mtime) if folder.exists() else []
    return reports[-1] if reports else None


def report_settings(report_dir: Path) -> dict[str, Any]:
    p = report_dir / "settings.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ------------------------------------------------------------------ review
@dataclass
class ReviewItem:
    name: str
    status: str
    suggestion: str
    rows: int
    chosen: str = ""


def load_review(report_dir: Path, project: Project) -> list[ReviewItem]:
    """The names and places awaiting a jurisdiction, with any choice already saved for the project."""
    saved = load_overrides(project)
    path = report_dir / "review_jurisdictions.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [ReviewItem(r["name"], r["status"], r["suggested_jurisdiction"], int(r["rows"] or 0),
                           saved.get(r["name"], "")) for r in csv.DictReader(fh)]


def load_revenue_conflicts(report_dir: Path) -> list[dict[str, str]]:
    path = report_dir / "review_revenue.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_overrides(project: Project) -> dict[str, str]:
    p = project.overrides_path
    return ashare.read_overrides(p) if p.exists() else {}


def save_overrides(project: Project, choices: dict[str, str]) -> Path:
    """Merge choices (name to jurisdiction code; an empty code removes a choice) into the project's overrides."""
    known = jurisdiction_codes()
    merged = load_overrides(project)
    for name, code in choices.items():
        code = code.strip().upper()
        if not code:
            merged.pop(name, None)
        elif code in known:
            merged[name] = code
        else:
            raise ValueError(f"{code} is not a jurisdiction code")
    path = project.overrides_path
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["name", "jurisdiction_id"])
        w.writerows(sorted(merged.items()))
    return path


def jurisdiction_codes() -> dict[str, str]:
    """Code to display name, for pickers."""
    return {r["jurisdiction_id"]: r["display_name"] for r in jurisdictions.registry_rows()}


# ------------------------------------------------------------------ data browsing
def ownership_rows(project: Project, search: str = "", limit: int = 500) -> list[dict[str, Any]]:
    """Ownership and control relations with names, jurisdictions and the source each rests on."""
    like = f"%{search.strip()}%"
    sql = """
        SELECT o.relation_id, h.reported_name AS holder, h.jurisdiction_id AS holder_j,
               d.reported_name AS held, d.jurisdiction_id AS held_j, o.relation_type, o.fraction,
               o.valid_from, s.title AS source_title, s.url AS source_url
        FROM ownership o
        JOIN entities h ON h.entity_id = o.holder_id
        JOIN entities d ON d.entity_id = o.held_id
        JOIN sources s ON s.source_id = o.source_id
        WHERE h.reported_name LIKE ? OR d.reported_name LIKE ? OR h.jurisdiction_id LIKE ? OR d.jurisdiction_id LIKE ?
        ORDER BY d.reported_name, o.fraction DESC LIMIT ?"""
    with project.open() as store:
        cur = store.conn.execute(sql, (like, like, like, like, limit))
        names = [c[0] for c in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]


def revenue_rows(project: Project, search: str = "", limit: int = 500) -> list[dict[str, Any]]:
    like = f"%{search.strip()}%"
    sql = """
        SELECT e.reported_name AS entity, f.period, f.operating_revenue, f.currency, f.consolidation,
               s.title AS source_title, s.url AS source_url
        FROM entity_financials f JOIN entities e USING (entity_id) JOIN sources s ON s.source_id = f.source_id
        WHERE e.reported_name LIKE ? ORDER BY f.operating_revenue DESC LIMIT ?"""
    with project.open() as store:
        cur = store.conn.execute(sql, (like, limit))
        names = [c[0] for c in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]


def open_url(url: str | None) -> bool:
    """Open a source document in the browser. Only web addresses are opened."""
    if url and url.lower().startswith(("https://", "http://")):
        return webbrowser.open(url)
    return False


# ------------------------------------------------------------------ Lab and snapshots
def export_lab(project: Project, folder: str | Path | None = None) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(folder) if folder else project.files / "lab_exports" / stamp
    with project.open() as store:
        export.lab_dataset(store, out)
    return out


def take_snapshot(project: Project, note: str | None = None, folder: str | Path | None = None) -> Path:
    out = Path(folder) if folder else project.files / "snapshots"
    with project.open() as store:
        return snapshot.export(store, out, note=note or None)


def list_snapshots(project: Project) -> list[dict[str, Any]]:
    with project.open() as store:
        rows = store.rows("snapshots")
    for r in rows:
        r["counts"] = json.loads(r["counts"]) if isinstance(r["counts"], str) else r["counts"]
    return sorted(rows, key=lambda r: r["created_utc"], reverse=True)


def snapshot_folder(project: Project, snapshot_id: str) -> Path | None:
    p = project.files / "snapshots" / snapshot_id
    return p if p.exists() else None


def verify_snapshot(folder: str | Path) -> list[str]:
    return snapshot.verify(folder)


# ------------------------------------------------------------------ checks
def check(project: Project) -> Report:
    with project.open() as store:
        return store.validate()


def table_descriptions() -> dict[str, str]:
    return {t: sc.SCHEMAS[t].description for t in SUMMARY_TABLES}
