"""Snapshots: freeze the store's content so that any figure can be regenerated (data model v1, s 4)."""

from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass
from pathlib import Path

from rscore import SCHEMA_GENERATION, __version__
from rscore import schema as sc
from rscore.canonical import canonical_csv, canonical_json, combine_hashes, sha256_text
from rscore.store import Store


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    created_utc: str
    table_hashes: dict[str, str]
    counts: dict[str, int]
    note: str | None = None


def table_csv(store: Store, table: str) -> str:
    schema = sc.SCHEMAS[table]
    return canonical_csv(store.rows(table), schema.column_names, schema.primary_key)


def table_hashes(store: Store) -> dict[str, str]:
    """Hash of every non-empty content table. Empty tables are left out, so that adding a table in a
    later schema generation never changes an existing snapshot identifier."""
    return {t: sha256_text(table_csv(store, t)) for t in sc.CONTENT_TABLES if store.count(t)}


def snapshot_id(store: Store) -> str:
    return combine_hashes(table_hashes(store))


def take(store: Store, note: str | None = None) -> Snapshot:
    """Record a snapshot of the store's current content and return it."""
    hashes = table_hashes(store)
    counts = {t: store.count(t) for t in hashes}
    created = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    snap = Snapshot(combine_hashes(hashes), created, hashes, counts, note)
    with store.conn:
        store.conn.execute(
            "INSERT INTO snapshots (snapshot_id, created_utc, schema_generation, table_hashes, counts, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (snap.snapshot_id, created, SCHEMA_GENERATION, canonical_json(hashes), canonical_json(counts), note),
        )
    return snap


def export(store: Store, directory: str | Path, note: str | None = None) -> Path:
    """Write every non-empty content table as canonical CSV plus ``manifest.json`` into
    ``directory/<snapshot_id>`` and record the snapshot. An existing identical export is reused."""
    snap = take(store, note)
    target = Path(directory) / snap.snapshot_id
    if (target / "manifest.json").exists():
        return target
    tmp = Path(directory) / f".tmp-{snap.snapshot_id}-{os.getpid()}"
    tmp.mkdir(parents=True, exist_ok=True)
    for table in snap.table_hashes:
        (tmp / f"{table}.csv").write_text(table_csv(store, table), encoding="utf-8", newline="")
    manifest = {
        "snapshot_id": snap.snapshot_id,
        "created_utc": snap.created_utc,
        "schema_generation": SCHEMA_GENERATION,
        "software": f"research-suite-core {__version__}",
        "table_hashes": snap.table_hashes,
        "counts": snap.counts,
        "note": note,
        "hash_rule": "SHA-256 of canonical CSV per table; snapshot_id = SHA-256 of sorted 'table:hash' lines",
    }
    (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return target


def verify(directory: str | Path) -> list[str]:
    """Check an exported snapshot against its manifest. Return a list of problems (empty if intact)."""
    path = Path(directory)
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    found = {}
    for table, expected in manifest["table_hashes"].items():
        f = path / f"{table}.csv"
        if not f.exists():
            problems.append(f"{table}.csv is missing")
            continue
        found[table] = sha256_text(f.read_text(encoding="utf-8"))
        if found[table] != expected:
            problems.append(f"{table}.csv has changed since export")
    if not problems and combine_hashes(found) != manifest["snapshot_id"]:
        problems.append("snapshot_id does not match the table hashes")
    return problems
