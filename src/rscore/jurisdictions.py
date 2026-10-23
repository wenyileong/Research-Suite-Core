"""The jurisdiction registry: ISO 3166-1 alpha-3 codes plus explicit records for special cases.

Codes and English short names come from ``data/iso3166.json``, the list the International Tax Network
Lab ships (extracted from the Debian iso-codes data, LGPL-2.1, via pycountry). Display names are kept as
the list gives them.

Only cases where the classification matters for tax research are given a ``kind``; every other code is
left unclassified (``kind`` empty) rather than guessed. ``parent_jurisdiction_id`` records sovereignty
only, never a shared tax system.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from rscore.store import Store

REGISTRY_SOURCE_ID = "rscore_iso3166"

_SAR = ("HKG", "MAC")
_CROWN_DEPENDENCIES = ("GGY", "IMN", "JEY")
#: British Overseas Territories that have their own ISO 3166-1 codes.
_UK_OVERSEAS_TERRITORIES = ("AIA", "BMU", "CYM", "FLK", "GIB", "IOT", "MSR", "PCN", "SGS", "SHN", "TCA", "VGB")

_NOTES = {
    "HKG": "Special administrative region of China with its own tax system.",
    "MAC": "Special administrative region of China with its own tax system.",
    "GGY": "Crown Dependency; not part of the United Kingdom; own tax system.",
    "IMN": "Crown Dependency; not part of the United Kingdom; own tax system.",
    "JEY": "Crown Dependency; not part of the United Kingdom; own tax system.",
}

SUPRANATIONAL = (
    {"jurisdiction_id": "SUP_EU", "display_name": "European Union", "note": "For EU-level rules such as directives."},
)


def iso_codes() -> dict[str, str]:
    """ISO 3166-1 alpha-3 code to English short name."""
    text = resources.files("rscore").joinpath("data/iso3166.json").read_text(encoding="utf-8")
    return dict(json.loads(text)["codes"])


def registry_source() -> dict[str, Any]:
    text = resources.files("rscore").joinpath("data/iso3166.json").read_text(encoding="utf-8")
    note = json.loads(text)["source"]
    return {
        "source_id": REGISTRY_SOURCE_ID,
        "title": "ISO 3166-1 alpha-3 codes and English short names",
        "custodian": "Debian iso-codes project (via pycountry)",
        "licence_class": "public_attribution",
        "licence_terms": "LGPL-2.1 (Debian iso-codes)",
        "coverage": "249 codes",
        "limitations": note + ". Classification of special cases added by research-suite-core.",
    }


def registry_rows() -> list[dict[str, Any]]:
    """Jurisdiction rows for every ISO code plus the supranational records, in insertion order."""
    rows: list[dict[str, Any]] = []
    for code, name in sorted(iso_codes().items()):
        kind, parent = None, None
        if code in _SAR:
            kind, parent = "special_administrative_region", "CHN"
        elif code in _CROWN_DEPENDENCIES:
            kind = "crown_dependency"
        elif code in _UK_OVERSEAS_TERRITORIES:
            kind, parent = "overseas_territory", "GBR"
        rows.append({
            "jurisdiction_id": code, "display_name": name, "iso3": code, "fictional": False,
            "parent_jurisdiction_id": parent, "kind": kind, "note": _NOTES.get(code),
        })
    for sup in SUPRANATIONAL:
        rows.append({**sup, "fictional": False, "kind": "supranational"})
    # Parents must be written before their children.
    rows.sort(key=lambda r: r.get("parent_jurisdiction_id") is not None)
    return rows


def seed(store: Store) -> int:
    """Write the registry source and every jurisdiction not yet in the store. Return how many were added."""
    if REGISTRY_SOURCE_ID not in store.keys("sources", "source_id"):
        store.insert("sources", [registry_source()])
    present = store.keys("jurisdictions", "jurisdiction_id")
    new = [r for r in registry_rows() if r["jurisdiction_id"] not in present]
    if new:
        store.insert("jurisdictions", new)
    return len(new)
