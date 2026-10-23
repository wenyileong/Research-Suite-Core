"""Export from the shared store to the tools' own formats (data model v1, s 5)."""

from __future__ import annotations

from pathlib import Path

from rscore import conventions as cv
from rscore import schema as sc
from rscore.canonical import canonical_csv
from rscore.store import Store

#: Tables the International Tax Network Lab requires in every dataset.
LAB_REQUIRED = ("sources", "jurisdictions", "entities", "ownership")


def lab_dataset(store: Store, directory: str | Path) -> list[Path]:
    """Write the Lab's tables as CSV files with exactly the Lab's columns, ready for the Lab's import.

    Columns the shared model adds (such as ``jurisdictions.kind``) are dropped, and so are ``SUP_``
    groupings, which the Lab does not recognise as jurisdictions. Required tables are written even when
    empty; optional tables only when they have rows. Redistribution limits are left to the Lab, which
    enforces them on export from its side.
    """
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for table, columns in sc.LAB_COLUMNS.items():
        rows = store.rows(table)
        if "jurisdiction_id" in columns:
            rows = [r for r in rows if not str(r["jurisdiction_id"]).startswith(cv.SUPRANATIONAL_PREFIX)]
        if not rows and table not in LAB_REQUIRED:
            continue
        text = canonical_csv(rows, columns, sc.SCHEMAS[table].primary_key)
        path = out / f"{table}.csv"
        path.write_text(text, encoding="utf-8", newline="")
        written.append(path)
    return written
