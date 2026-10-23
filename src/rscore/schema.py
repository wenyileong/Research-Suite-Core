"""Table definitions of the shared data model, version 1 (``docs/data_model_v1.md``).

Tables shared with the International Tax Network Lab keep the Lab's names and columns; columns the
shared model adds to them are listed in ``LAB_COLUMNS`` so that export can drop them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rscore import conventions as cv

# Column types.
STR, FLOAT, INT, BOOL, DATE, PERIOD = "str", "float", "int", "bool", "date", "period"
ID, JURISDICTION, CURRENCY, LANGUAGE = "id", "jurisdiction", "currency", "language"

_TRUE = {"true", "1", "yes", "y", "t"}
_FALSE = {"false", "0", "no", "n", "f"}


@dataclass(frozen=True)
class Column:
    name: str
    type: str = STR
    nullable: bool = True
    choices: tuple[str, ...] | None = None
    minimum: float | None = None
    maximum: float | None = None
    references: str | None = None  # "table.column" for a foreign key


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]
    description: str
    #: False for bookkeeping tables, which are not part of a snapshot's content.
    content: bool = True

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def column(self, name: str) -> Column:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(f"{self.name}.{name}")


def _c(name: str, type: str = STR, *, req: bool = False, **kw: Any) -> Column:
    return Column(name=name, type=type, nullable=not req, **kw)


def _src() -> Column:
    return _c("source_id", ID, req=True, references="sources.source_id")


def _jur(name: str = "jurisdiction_id", *, req: bool = True) -> Column:
    return _c(name, JURISDICTION, req=req, references="jurisdictions.jurisdiction_id")


_TABLES: tuple[TableSchema, ...] = (
    TableSchema(
        "sources",
        (
            _c("source_id", ID, req=True),
            _c("title", req=True),
            _c("custodian"),
            _c("url"),
            _c("retrieval_date", DATE),
            _c("licence_class", req=True, choices=cv.LICENCE_CLASSES),
            _c("licence_terms"),
            _c("permitted_uses"),
            _c("redistribution"),
            _c("coverage"),
            _c("limitations"),
            _c("oscola_citation"),
            _c("content_sha256"),
            _c("extraction_method"),
        ),
        ("source_id",),
        "Where every record came from and on what terms.",
    ),
    TableSchema(
        "jurisdictions",
        (
            _c("jurisdiction_id", JURISDICTION, req=True),
            _c("display_name", req=True),
            _c("iso3"),
            _c("fictional", BOOL, req=True),
            _jur("parent_jurisdiction_id", req=False),
            _c("kind", choices=cv.JURISDICTION_KINDS),
            _c("valid_from", DATE),
            _c("valid_to", DATE),
            _c("note"),
        ),
        ("jurisdiction_id",),
        "Taxing territories. Real: ISO 3166-1 alpha-3. Fictional: FIC_. Groupings: SUP_.",
    ),
    TableSchema(
        "jurisdiction_aliases",
        (
            _c("alias", req=True),
            _c("language", LANGUAGE, req=True),
            _jur(),
            _src(),
        ),
        ("alias", "language"),
        "Other names for a jurisdiction, for importers.",
    ),
    TableSchema(
        "jurisdiction_attributes",
        (
            _jur(),
            _c("attribute", req=True),
            _c("period", PERIOD, req=True),
            _c("value", FLOAT, req=True),
            _c("unit", req=True),
            _c("currency", CURRENCY),
            _src(),
        ),
        ("jurisdiction_id", "attribute", "period"),
        "Contextual time series such as GDP.",
    ),
    TableSchema(
        "entities",
        (
            _c("entity_id", ID, req=True),
            _c("reported_name", req=True),
            _jur(),
            _c("entity_type", req=True),
            _c("entity_type_rule"),
            _c("is_natural_person", BOOL, req=True),
            _c("valid_from", DATE),
            _c("valid_to", DATE),
            _src(),
        ),
        ("entity_id",),
        "Legal entities. Natural persons are excluded before import.",
    ),
    TableSchema(
        "ownership",
        (
            _c("relation_id", ID, req=True),
            _c("holder_id", ID, req=True, references="entities.entity_id"),
            _c("held_id", ID, req=True, references="entities.entity_id"),
            _c("relation_type", req=True, choices=cv.RELATION_TYPES),
            _c("share_class"),
            _c("fraction", FLOAT, minimum=0.0, maximum=1.0),
            _c("value_amount", FLOAT, minimum=0.0),
            _c("value_currency", CURRENCY),
            _c("valuation_basis"),
            _c("direct", BOOL, req=True),
            _c("valid_from", DATE, req=True),
            _c("valid_to", DATE),
            _src(),
        ),
        ("relation_id",),
        "Direct relations stored holder to held. Indirect holdings are derived, never stored.",
    ),
    TableSchema(
        "entity_financials",
        (
            _c("entity_id", ID, req=True, references="entities.entity_id"),
            _c("period", PERIOD, req=True),
            _c("operating_revenue", FLOAT, req=True, minimum=0.0),
            _c("currency", CURRENCY, req=True),
            _c("consolidation", req=True, choices=cv.CONSOLIDATION),
            _src(),
        ),
        ("entity_id", "period"),
        "Operating revenue per entity and period.",
    ),
    TableSchema(
        "flows",
        (
            _c("flow_id", ID, req=True),
            _c("from_kind", req=True, choices=cv.PARTY_KINDS),
            _c("from_id", ID, req=True),
            _c("to_kind", req=True, choices=cv.PARTY_KINDS),
            _c("to_id", ID, req=True),
            _c("flow_type", req=True, choices=cv.FLOW_TYPES),
            _c("amount", FLOAT, req=True),
            _c("currency", CURRENCY, req=True),
            _c("period", PERIOD, req=True),
            _c("valuation_basis"),
            _src(),
        ),
        ("flow_id",),
        "Payments and investment between entities or jurisdictions.",
    ),
    TableSchema(
        "instruments",
        (
            _c("instrument_id", ID, req=True),
            _c("instrument_type", req=True, choices=cv.INSTRUMENT_TYPES),
            _c("title", req=True),
            _c("short_title"),
            _c("signed_date", DATE),
            _c("in_force_date", DATE),
            _c("effective_from", DATE),
            _c("terminated_date", DATE),
            _c("oscola_citation"),
            _src(),
        ),
        ("instrument_id",),
        "Treaties, the Multilateral Instrument, statutes, regulations and guidance.",
    ),
    TableSchema(
        "instrument_parties",
        (
            _c("instrument_id", ID, req=True, references="instruments.instrument_id"),
            _jur(),
            _c("ratification_date", DATE),
            _c("mli_covered", BOOL),
            _src(),
        ),
        ("instrument_id", "jurisdiction_id"),
        "Parties to an instrument; mli_covered marks a covered tax agreement under the MLI.",
    ),
    TableSchema(
        "provisions",
        (
            _c("provision_id", ID, req=True),
            _c("instrument_id", ID, req=True, references="instruments.instrument_id"),
            _c("pinpoint", req=True),
            _c("heading"),
            _c("text_sha256"),
            _c("valid_from", DATE),
            _c("valid_to", DATE),
            _src(),
        ),
        ("provision_id",),
        "A pinpointed rule in an instrument.",
    ),
    TableSchema(
        "regime_values",
        (
            _jur(),
            _c("variable", ID, req=True),
            _c("valid_from", DATE, req=True),
            _c("valid_to", DATE),
            _c("layer"),
            _c("value", req=True),
            _c("value_type", req=True, choices=cv.VALUE_TYPES),
            _c("unit"),
            _c("rule_status", req=True, choices=cv.RULE_STATUSES),
            _c("verified", BOOL, req=True),
            _c("provision_id", ID, references="provisions.provision_id"),
            _src(),
            _c("note"),
        ),
        ("jurisdiction_id", "variable", "valid_from"),
        "Coded rules in long form: one variable per row, with type, validity and status.",
    ),
    TableSchema(
        "authorities",
        (
            _c("authority_id", ID, req=True),
            _c("kind", req=True, choices=cv.AUTHORITY_KINDS),
            _c("oscola_citation", req=True),
            _c("court_or_body"),
            _jur(req=False),
            _c("decision_date", DATE),
            _src(),
        ),
        ("authority_id",),
        "Cases, rulings and official guidance.",
    ),
    TableSchema(
        "propositions",
        (
            _c("proposition_id", ID, req=True),
            _c("text", req=True),
            _c("status", req=True, choices=cv.PROPOSITION_STATUSES),
            _c("verified_by"),
            _c("verified_on", DATE),
            _c("note"),
        ),
        ("proposition_id",),
        "Legal claims the software relies on.",
    ),
    TableSchema(
        "proposition_links",
        (
            _c("proposition_id", ID, req=True, references="propositions.proposition_id"),
            _c("target_table", req=True, choices=cv.LINK_TABLES),
            _c("target_id", req=True),
            _c("role", req=True, choices=cv.LINK_ROLES),
            _c("pinpoint"),
        ),
        ("proposition_id", "target_table", "target_id"),
        "Links from a proposition to what supports, qualifies or contradicts it.",
    ),
    TableSchema(
        "meta",
        (_c("key", req=True), _c("value", req=True)),
        ("key",),
        "Store bookkeeping: schema generation and creation time.",
        content=False,
    ),
    TableSchema(
        "snapshots",
        (
            _c("snapshot_id", req=True),
            _c("created_utc", req=True),
            _c("schema_generation", INT, req=True),
            _c("table_hashes", req=True),
            _c("counts", req=True),
            _c("note"),
        ),
        ("snapshot_id", "created_utc"),
        "Snapshots taken of the store.",
        content=False,
    ),
)

SCHEMAS: dict[str, TableSchema] = {t.name: t for t in _TABLES}
#: Tables in dependency order (referenced tables first).
TABLE_ORDER: tuple[str, ...] = tuple(t.name for t in _TABLES)
CONTENT_TABLES: tuple[str, ...] = tuple(t.name for t in _TABLES if t.content)

#: The Lab's exact columns for the tables the two share (Lab schema generation 2).
LAB_COLUMNS: dict[str, tuple[str, ...]] = {
    "sources": ("source_id", "title", "custodian", "url", "retrieval_date", "licence_class", "licence_terms",
                "permitted_uses", "redistribution", "coverage", "limitations", "oscola_citation"),
    "jurisdictions": ("jurisdiction_id", "display_name", "iso3", "fictional", "parent_jurisdiction_id"),
    "jurisdiction_attributes": ("jurisdiction_id", "attribute", "period", "value", "unit", "currency", "source_id"),
    "entities": ("entity_id", "reported_name", "jurisdiction_id", "entity_type", "entity_type_rule",
                 "is_natural_person", "valid_from", "valid_to", "source_id"),
    "ownership": ("relation_id", "holder_id", "held_id", "relation_type", "share_class", "fraction", "value_amount",
                  "value_currency", "valuation_basis", "direct", "valid_from", "valid_to", "source_id"),
    "entity_financials": ("entity_id", "period", "operating_revenue", "currency", "consolidation", "source_id"),
}


def coerce(column: Column, raw: Any) -> Any:
    """Convert one value to the column's type, or raise ``ValueError`` with a plain-English reason.

    Empty values become ``None``. Strings are accepted for every type, so rows can come straight from CSV.
    """
    if cv.is_empty(raw):
        return None
    t = column.type
    if t == BOOL:
        if isinstance(raw, bool):
            return raw
        text = str(raw).strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise ValueError(f"not a true/false value: {raw!r}")
    if t in (FLOAT, INT):
        if isinstance(raw, bool):
            raise ValueError(f"not a number: {raw!r}")
        try:
            value = float(raw) if t == FLOAT else int(str(raw).strip())
        except (TypeError, ValueError):
            raise ValueError(f"not a{'n integer' if t == INT else ' number'}: {raw!r}") from None
        if t == FLOAT and (value != value or value in (float("inf"), float("-inf"))):
            raise ValueError(f"not a finite number: {raw!r}")
        if column.minimum is not None and value < column.minimum:
            raise ValueError(f"{value} is below the minimum {column.minimum}")
        if column.maximum is not None and value > column.maximum:
            raise ValueError(f"{value} is above the maximum {column.maximum}")
        return value
    text = str(raw).strip()
    if t == DATE:
        cv.parse_date(text)
    elif t == PERIOD:
        cv.parse_period(text)
    elif t == ID and not cv.ID_RE.match(text):
        raise ValueError(f"not a valid identifier (1 to 64 of A-Z a-z 0-9 _ . : -): {text!r}")
    elif t == JURISDICTION and not cv.is_jurisdiction_id(text):
        raise ValueError(f"not an ISO 3166-1 alpha-3 code or a FIC_/SUP_ identifier: {text!r}")
    elif t == CURRENCY and not cv.CURRENCY_RE.match(text):
        raise ValueError(f"not an ISO 4217 currency code: {text!r}")
    elif t == LANGUAGE and not cv.LANGUAGE_RE.match(text):
        raise ValueError(f"not a language tag such as 'en' or 'zh-Hans': {text!r}")
    if column.choices is not None and text not in column.choices:
        raise ValueError(f"{text!r} is not one of: {', '.join(column.choices)}")
    return text
