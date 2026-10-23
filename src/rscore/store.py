"""The shared store: one SQLite file per project, with versioned migrations.

SQLite comes with Python, so the store adds nothing to a tool's executable. Rows are validated against
``rscore.schema`` before they are written; a batch that fails validation writes nothing.
"""

from __future__ import annotations

import datetime as _dt
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

from rscore import SCHEMA_GENERATION
from rscore import conventions as cv
from rscore import schema as sc
from rscore.validation import Report, ValidationError

_SQL_TYPES = {sc.FLOAT: "REAL", sc.INT: "INTEGER", sc.BOOL: "INTEGER"}


def _ddl(table: sc.TableSchema) -> str:
    cols = []
    for c in table.columns:
        cols.append(f'"{c.name}" {_SQL_TYPES.get(c.type, "TEXT")}{"" if c.nullable else " NOT NULL"}')
    cols.append("PRIMARY KEY (" + ", ".join(f'"{k}"' for k in table.primary_key) + ")")
    for c in table.columns:
        if c.references:
            ref_table, ref_col = c.references.split(".")
            cols.append(f'FOREIGN KEY ("{c.name}") REFERENCES "{ref_table}" ("{ref_col}")')
    return f'CREATE TABLE IF NOT EXISTS "{table.name}" (\n  ' + ",\n  ".join(cols) + "\n)"


def _create_generation_1(conn: sqlite3.Connection) -> None:
    for name in sc.TABLE_ORDER:
        conn.execute(_ddl(sc.SCHEMAS[name]))


#: Migration that brings a store up to each generation. Add a function here and raise
#: ``rscore.SCHEMA_GENERATION`` whenever the schema changes; never edit a released migration.
MIGRATIONS = {1: _create_generation_1}


class StoreError(RuntimeError):
    pass


class Store:
    """A project store. Use as a context manager, or call :meth:`close`."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    # -------------------------------------------------------------- lifecycle
    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    @property
    def generation(self) -> int:
        row = self.conn.execute("SELECT value FROM meta WHERE key = 'schema_generation'").fetchone()
        return int(row[0])

    def _migrate(self) -> None:
        has_meta = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'").fetchone()
        current = 0
        if has_meta:
            row = self.conn.execute("SELECT value FROM meta WHERE key = 'schema_generation'").fetchone()
            current = int(row[0]) if row else 0
        if current > SCHEMA_GENERATION:
            self.conn.close()
            raise StoreError(f"{self.path.name} was made by a newer version (schema generation {current}); "
                             f"this version reads up to generation {SCHEMA_GENERATION}")
        with self.conn:
            for gen in range(current + 1, SCHEMA_GENERATION + 1):
                MIGRATIONS[gen](self.conn)
                self.conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_generation', ?)",
                                  (str(gen),))
            if current == 0:
                now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
                self.conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('created_utc', ?)", (now,))

    # -------------------------------------------------------------- reading
    def rows(self, table: str) -> list[dict[str, Any]]:
        """All rows of a table, with booleans as ``bool``."""
        schema = sc.SCHEMAS[table]
        cur = self.conn.execute(f'SELECT * FROM "{table}"')
        names = [d[0] for d in cur.description]
        bools = {c.name for c in schema.columns if c.type == sc.BOOL}
        out = []
        for values in cur.fetchall():
            row = dict(zip(names, values))
            for b in bools:
                if row[b] is not None:
                    row[b] = bool(row[b])
            out.append(row)
        return out

    def keys(self, table: str, column: str) -> set[Any]:
        return {r[0] for r in self.conn.execute(f'SELECT "{column}" FROM "{table}"')}

    def count(self, table: str) -> int:
        return self.conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

    # -------------------------------------------------------------- writing
    def insert(self, table: str, rows: Iterable[dict[str, Any]], *, replace: bool = False) -> Report:
        """Validate and write rows. Raise :class:`ValidationError` (writing nothing) if any row fails.

        Returns the report, which may hold warnings. With ``replace``, a row whose primary key exists is
        overwritten; otherwise a duplicate key is an error.
        """
        if table not in sc.SCHEMAS or not sc.SCHEMAS[table].content:
            raise KeyError(f"not a content table: {table}")
        schema = sc.SCHEMAS[table]
        report = Report()
        parsed = [self._parse_row(schema, n, row, report) for n, row in enumerate(rows, start=1)]
        self._check_keys(schema, parsed, report, replace)
        self._check_references(schema, parsed, report)
        if not report.ok:
            raise ValidationError(report)
        names = schema.column_names
        sql = (f'INSERT {"OR REPLACE " if replace else ""}INTO "{table}" ('
               + ", ".join(f'"{n}"' for n in names) + ") VALUES (" + ", ".join("?" for _ in names) + ")")
        with self.conn:
            self.conn.executemany(sql, [[_to_sql(r[n]) for n in names] for r in parsed])
        return report

    # -------------------------------------------------------------- checks
    def _parse_row(self, schema: sc.TableSchema, n: int, raw: dict[str, Any], report: Report) -> dict[str, Any]:
        where = f"row {n}"
        unknown = set(raw) - set(schema.column_names)
        if unknown:
            report.error(schema.name, where, f"unknown column(s): {', '.join(sorted(unknown))}")
        row: dict[str, Any] = {}
        for col in schema.columns:
            try:
                row[col.name] = sc.coerce(col, raw.get(col.name))
            except ValueError as exc:
                report.error(schema.name, where, f"{col.name}: {exc}")
                row[col.name] = None
                continue
            if row[col.name] is None and not col.nullable:
                report.error(schema.name, where, f"{col.name} is required")
        _row_rules(schema.name, where, row, report)
        return row

    def _check_keys(self, schema: sc.TableSchema, rows: Sequence[dict[str, Any]], report: Report,
                    replace: bool) -> None:
        seen: set[tuple] = set()
        existing: set[tuple] = set()
        if not replace:
            cols = ", ".join(f'"{k}"' for k in schema.primary_key)
            existing = {tuple(r) for r in self.conn.execute(f'SELECT {cols} FROM "{schema.name}"')}
        for n, row in enumerate(rows, start=1):
            key = tuple(_to_sql(row[k]) for k in schema.primary_key)
            if None in key:
                continue  # already reported as a missing required value
            if key in seen:
                report.error(schema.name, f"row {n}", f"duplicate key in this batch: {key}")
            elif key in existing:
                report.error(schema.name, f"row {n}", f"key already in the store: {key} (use replace to overwrite)")
            seen.add(key)

    def _check_references(self, schema: sc.TableSchema, rows: Sequence[dict[str, Any]], report: Report) -> None:
        for col in schema.columns:
            if not col.references:
                continue
            ref_table, ref_col = col.references.split(".")
            known = self.keys(ref_table, ref_col)
            if ref_table == schema.name:  # self-reference: rows in the same batch count
                known |= {r[ref_col] for r in rows}
            for n, row in enumerate(rows, start=1):
                value = row[col.name]
                if value is not None and value not in known:
                    report.error(schema.name, f"row {n}", f"{col.name} {value!r} is not in {ref_table}")
        self._check_synthetic(schema, rows, report)
        if schema.name == "flows":
            for n, row in enumerate(rows, start=1):
                for side in ("from", "to"):
                    kind, value = row[f"{side}_kind"], row[f"{side}_id"]
                    if kind is None or value is None:
                        continue
                    target = ("entities", "entity_id") if kind == "entity" else ("jurisdictions", "jurisdiction_id")
                    if value not in self.keys(*target):
                        report.error("flows", f"row {n}", f"{side}_id {value!r} is not in {target[0]}")
        if schema.name == "proposition_links":
            pk = {"provisions": "provision_id", "authorities": "authority_id"}
            for n, row in enumerate(rows, start=1):
                t, value = row["target_table"], row["target_id"]
                if t is None or value is None:
                    continue
                if t == "regime_values":
                    found = value in {"|".join(k) for k in self.conn.execute(
                        'SELECT jurisdiction_id, variable, valid_from FROM regime_values')}
                    hint = " (use jurisdiction_id|variable|valid_from)"
                else:
                    found, hint = value in self.keys(t, pk[t]), ""
                if not found:
                    report.error("proposition_links", f"row {n}", f"target {value!r} is not in {t}{hint}")

    def _check_synthetic(self, schema: sc.TableSchema, rows: Sequence[dict[str, Any]], report: Report) -> None:
        """Synthetic data must not be attributed to real jurisdictions (as in the Lab's validation)."""
        if schema.name not in ("entities", "regime_values"):
            return
        synthetic = {r[0] for r in self.conn.execute(
            "SELECT source_id FROM sources WHERE licence_class = 'synthetic'")}
        for n, row in enumerate(rows, start=1):
            jid = row.get("jurisdiction_id")
            if not jid or jid.startswith(cv.FICTIONAL_PREFIX):
                continue
            if schema.name == "entities" and row.get("source_id") in synthetic:
                report.error("entities", f"row {n}", f"synthetic record attributed to real jurisdiction {jid!r}")
            if schema.name == "regime_values":
                if row.get("rule_status") == "synthetic_assumption":
                    report.error("regime_values", f"row {n}",
                                 f"synthetic assumption attributed to real jurisdiction {jid!r}")
                elif row.get("verified") is False and row.get("source_id") not in synthetic:
                    report.warning("regime_values", f"row {n}",
                                   "legal row not yet verified; results relying on it should be flagged")

    def validate(self) -> Report:
        """Re-check the whole store as it now stands: every row (useful after edits made outside this
        library), plus group-level warnings that a single batch cannot show: current equity in one entity
        summing above 1, and ownership cycles."""
        report = Report()
        for name in sc.CONTENT_TABLES:
            schema = sc.SCHEMAS[name]
            rows = self.rows(name)
            sub = Report()
            parsed = [self._parse_row(schema, n, row, sub) for n, row in enumerate(rows, start=1)]
            self._check_references(schema, parsed, sub)
            keys = ["|".join(str(r[k]) for k in schema.primary_key) for r in rows]
            for issue in sub.issues:
                where = issue.where
                if where.startswith("row ") and where[4:].isdigit():
                    where = keys[int(where[4:]) - 1]
                report.issues.append(type(issue)(issue.level, name, where, issue.message))
        for table, rowid, parent, _ in self.conn.execute("PRAGMA foreign_key_check").fetchall():
            report.error(table, f"rowid {rowid}", f"refers to a missing row in {parent}")
        self._group_warnings(report)
        return report

    def _group_warnings(self, report: Report) -> None:
        ownership = self.rows("ownership")
        totals: dict[tuple[str, str], float] = {}
        graph: dict[str, set[str]] = {}
        for o in ownership:
            if o["relation_type"] == "equity" and o["valid_to"] is None and o["fraction"] is not None:
                key = (o["held_id"], o["share_class"] or "")
                totals[key] = totals.get(key, 0.0) + o["fraction"]
            if o["holder_id"] != o["held_id"]:
                graph.setdefault(o["holder_id"], set()).add(o["held_id"])
        for (held, share_class), total in sorted(totals.items()):
            if total > 1 + EQUITY_TOLERANCE:
                label = f"{held!r}" + (f" class {share_class}" if share_class else "")
                report.warning("ownership", held, f"current equity fractions in {label} sum to {total:.4f}")
        cycle = _find_cycle(graph)
        if cycle:
            report.warning("ownership", cycle[0], "ownership cycle (cross-holding): " + " -> ".join(cycle))


#: Tolerance before current equity fractions in one entity are reported as summing above 1 (as in the Lab).
EQUITY_TOLERANCE = 1e-6


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    """Return one directed cycle as a list of nodes (first node repeated at the end), or None."""
    state: dict[str, int] = {}  # 1 = on the current path, 2 = finished
    for start in sorted(graph):
        if start in state:
            continue
        path, stack = [start], [iter(sorted(graph.get(start, ())))]
        state[start] = 1
        while stack:
            nxt = next(stack[-1], None)
            if nxt is None:
                state[path.pop()] = 2
                stack.pop()
            elif state.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt]
            elif nxt not in state:
                state[nxt] = 1
                path.append(nxt)
                stack.append(iter(sorted(graph.get(nxt, ()))))
    return None


def _to_sql(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    return value


def _row_rules(table: str, where: str, row: dict[str, Any], report: Report) -> None:
    """Rules within one row (data model v1, s 3)."""
    start, end = row.get("valid_from"), row.get("valid_to")
    if start and end and end < start:
        report.error(table, where, f"valid_to {end} is earlier than valid_from {start}")
    if table == "ownership":
        if row.get("holder_id") and row.get("holder_id") == row.get("held_id"):
            report.warning(table, where, f"{row['holder_id']!r} holds itself (treasury shares?)")
        if row.get("direct") is False:
            report.error(table, where, "only direct relations are stored; indirect holdings are derived")
        if row.get("value_amount") is not None and not row.get("value_currency"):
            report.error(table, where, "value_amount requires value_currency")
        if row.get("fraction") is None:
            report.warning(table, where, "fraction not reported; it is never imputed")
    if table == "entities" and row.get("is_natural_person") is True:
        report.error(table, where, "natural persons must be excluded or pseudonymised before import")
    if table == "jurisdictions":
        jid, fictional, kind = row.get("jurisdiction_id"), row.get("fictional"), row.get("kind")
        if jid and fictional is not None and fictional != jid.startswith(cv.FICTIONAL_PREFIX):
            report.error(table, where, "fictional must be true exactly when the identifier starts with FIC_")
        if jid and row.get("iso3") and (fictional or row["iso3"] != jid):
            report.error(table, where, "iso3, where given, must equal the identifier of a real jurisdiction")
        if jid and jid.startswith(cv.SUPRANATIONAL_PREFIX) and kind not in (None, "supranational"):
            report.error(table, where, "a SUP_ identifier must have kind 'supranational'")
        if jid and row.get("parent_jurisdiction_id") == jid:
            report.error(table, where, "a jurisdiction cannot be its own parent")
    if table == "regime_values":
        _regime_rules(where, row, report)


def _regime_rules(where: str, row: dict[str, Any], report: Report) -> None:
    vt, value = row.get("value_type"), row.get("value")
    if vt and value is not None:
        try:
            if vt in ("fraction", "rate", "number"):
                number = float(value)
                if number != number or number in (float("inf"), float("-inf")):
                    raise ValueError("not a finite number")
                if vt in ("fraction", "rate") and not 0.0 <= number <= 1.0:
                    raise ValueError("a fraction must lie in [0, 1]")
                if vt == "rate" and number > cv.RATE_MAX:
                    raise ValueError(f"a rate is capped at {cv.RATE_MAX}")
            elif vt == "bool":
                sc.coerce(sc.Column("value", sc.BOOL), value)
            elif vt == "date":
                cv.parse_date(value)
        except ValueError as exc:
            report.error("regime_values", where, f"value {value!r} does not fit value_type {vt}: {exc}")
    if row.get("verified") is True and row.get("rule_status") not in (None, "source_backed"):
        report.error("regime_values", where, "a verified row must be source_backed")
    if row.get("rule_status") == "source_backed" and not row.get("provision_id"):
        report.warning("regime_values", where, "source_backed row names no provision_id")
