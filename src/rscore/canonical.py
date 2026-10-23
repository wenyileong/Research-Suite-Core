"""Canonical serialisation and hashing (data model v1, s 4).

The rules are those of the International Tax Network Lab (``taxnetlab/canonical.py``, the author's own
code), so that a table exported from the shared store hashes the same way the Lab hashes it:

* rows sorted by primary key, columns in schema order;
* floats in Python's shortest round-trip form, integers in decimal, booleans ``true``/``false``;
* empty values as empty strings, UTF-8 text, lines ending in ``\\n``.

The result is valid CSV. Hashes detect change; they do not establish that data are authentic or correct.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from typing import Any, Iterable, Sequence


def format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    return str(value)


def canonical_csv(rows: Iterable[dict[str, Any]], columns: Sequence[str], primary_key: Sequence[str]) -> str:
    def key(row: dict[str, Any]) -> tuple[str, ...]:
        return tuple(format_cell(row.get(k)) for k in primary_key)

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(list(columns))
    for row in sorted(rows, key=key):
        writer.writerow([format_cell(row.get(c)) for c in columns])
    return buf.getvalue()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no insignificant whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def combine_hashes(named: dict[str, str]) -> str:
    """Hash of several named hashes, independent of insertion order."""
    return sha256_text("".join(f"{name}:{named[name]}\n" for name in sorted(named)))
