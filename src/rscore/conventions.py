"""Value conventions shared by every table (data model v1, s 1).

They follow the International Tax Network Lab's conventions unchanged (its project plan v2.1, s 5.1), with
one addition: the ``SUP_`` prefix for groupings that are not ISO territories, such as the European Union.
"""

from __future__ import annotations

import datetime as _dt
import math
import re
from typing import Any

FICTIONAL_PREFIX = "FIC_"
SUPRANATIONAL_PREFIX = "SUP_"

ISO3_RE = re.compile(r"^[A-Z]{3}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
ID_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,64}$")
YEAR_RE = re.compile(r"^\d{4}$")
QUARTER_RE = re.compile(r"^\d{4}Q[1-4]$")
LANGUAGE_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")

#: Highest permitted tax rate. A rate of 100% would make later formulas degenerate (as in the Lab).
RATE_MAX = 0.9999

# Closed vocabularies shared with the Lab.
RELATION_TYPES = ("equity", "voting", "control", "economic_interest")
LICENCE_CLASSES = ("public", "public_attribution", "licensed_no_redistribution", "synthetic")
RULE_STATUSES = ("source_backed", "derived", "synthetic_assumption")
CONSOLIDATION = ("unconsolidated", "deconsolidated", "consolidated")

# Closed vocabularies new in the shared model.
JURISDICTION_KINDS = (
    "sovereign_state",
    "special_administrative_region",
    "crown_dependency",
    "overseas_territory",
    "other_territory",
    "supranational",
    "fictional",
)
FLOW_TYPES = ("dividend", "interest", "royalty", "service_fee", "fdi_position", "fdi_flow", "other")
PARTY_KINDS = ("entity", "jurisdiction")
INSTRUMENT_TYPES = (
    "bilateral_treaty",
    "multilateral_instrument",
    "domestic_statute",
    "regulation",
    "guidance",
    "other",
)
VALUE_TYPES = ("fraction", "rate", "number", "text", "bool", "date", "choice")
AUTHORITY_KINDS = ("judgment", "ruling", "guidance", "commentary", "other")
PROPOSITION_STATUSES = ("draft", "verified", "disputed", "superseded")
LINK_TABLES = ("provisions", "authorities", "regime_values")
LINK_ROLES = ("supports", "qualifies", "contradicts")


def is_empty(value: Any) -> bool:
    """True for ``None``, empty or blank strings and NaN."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and not value.strip()


def is_jurisdiction_id(value: str) -> bool:
    """ISO 3166-1 alpha-3, or a ``FIC_`` or ``SUP_`` identifier."""
    if ISO3_RE.match(value):
        return True
    for prefix in (FICTIONAL_PREFIX, SUPRANATIONAL_PREFIX):
        if value.startswith(prefix) and len(value) > len(prefix) and ID_RE.match(value):
            return True
    return False


def parse_date(value: str) -> _dt.date:
    """Parse an ISO 8601 calendar date (``YYYY-MM-DD``); raise ``ValueError`` otherwise."""
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f"not an ISO 8601 date (YYYY-MM-DD): {value!r}")
    return _dt.date.fromisoformat(value)


def parse_period(value: str) -> tuple[_dt.date, _dt.date]:
    """Return the first and last day of a period.

    A period is a year (``2025``), a quarter (``2025Q1``) or a closed date range
    (``2025-01-01/2025-06-30``). Raise ``ValueError`` for anything else.
    """
    if not isinstance(value, str):
        raise ValueError(f"not a period: {value!r}")
    if YEAR_RE.match(value):
        year = int(value)
        return _dt.date(year, 1, 1), _dt.date(year, 12, 31)
    if QUARTER_RE.match(value):
        year, quarter = int(value[:4]), int(value[5])
        start = _dt.date(year, 3 * quarter - 2, 1)
        end_month = 3 * quarter
        end = (_dt.date(year + 1, 1, 1) if end_month == 12 else _dt.date(year, end_month + 1, 1)) - _dt.timedelta(1)
        return start, end
    if "/" in value:
        first, _, last = value.partition("/")
        start, end = parse_date(first), parse_date(last)
        if end < start:
            raise ValueError(f"period ends before it starts: {value!r}")
        return start, end
    raise ValueError(f"not a period (YYYY, YYYYQn or YYYY-MM-DD/YYYY-MM-DD): {value!r}")
