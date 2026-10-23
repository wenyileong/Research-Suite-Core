"""Map place names (Chinese or English) to jurisdiction codes, without guessing.

Every alias found in the text is located. A match lying inside a longer match is dropped (内蒙古 is not
Mongolia; 印度尼西亚 is not India; New Jersey is not Jersey). Generic words for China (中国, 境内) give way
to any more specific place (中国香港 is Hong Kong). If one jurisdiction remains, it is the answer; if none
or several remain, the place goes to review. A user's overrides always come first.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources

from rscore.store import Store

ALIAS_SOURCE_ID = "rscore_place_aliases"


@dataclass(frozen=True)
class PlaceMatch:
    code: str | None
    status: str  # "override", "matched", "unmatched", "ambiguous", "empty"
    candidates: tuple[str, ...] = ()


def _load() -> dict:
    text = resources.files("rscore").joinpath("data/place_aliases.json").read_text(encoding="utf-8")
    return json.loads(text)


def _is_latin(alias: str) -> bool:
    return all(ord(ch) < 0x3000 for ch in alias)


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("　", " ")).strip()


class PlaceMatcher:
    def __init__(self, overrides: dict[str, str] | None = None):
        data = _load()
        self.generic = set(data["generic_chn"])
        entries: list[tuple[str, str]] = [(a, "CHN") for a in data["generic_chn"]]
        for code, aliases in data["aliases"].items():
            entries += [(a, code) for a in aliases]
        self.entries = entries
        self.patterns = []
        for alias, code in entries:
            if _is_latin(alias):
                pat = re.compile(r"(?<![A-Za-z])" + re.escape(alias) + r"(?![A-Za-z])", re.I)
            else:
                pat = re.compile(re.escape(alias))
            self.patterns.append((pat, alias, code))
        self.overrides = {normalise(k): v for k, v in (overrides or {}).items()}

    def match(self, text: str | None) -> PlaceMatch:
        if text is None or not normalise(text):
            return PlaceMatch(None, "empty")
        place = normalise(text)
        if place in self.overrides:
            return PlaceMatch(self.overrides[place], "override")
        hits = []
        for pat, alias, code in self.patterns:
            for m in pat.finditer(place):
                hits.append((m.start(), m.end(), alias, code))
        # Drop hits inside a longer hit.
        kept = [h for h in hits
                if not any(o is not h and o[0] <= h[0] and h[1] <= o[1] and (o[1] - o[0]) > (h[1] - h[0]) for o in hits)]
        specific = {h[3] for h in kept if h[2] not in self.generic}
        codes = specific or {h[3] for h in kept}
        if len(codes) == 1:
            return PlaceMatch(codes.pop(), "matched")
        if not codes:
            return PlaceMatch(None, "unmatched")
        return PlaceMatch(None, "ambiguous", tuple(sorted(codes)))


def seed_aliases(store: Store) -> int:
    """Write the alias list into ``jurisdiction_aliases`` (for inspection and for other tools)."""
    if ALIAS_SOURCE_ID not in store.keys("sources", "source_id"):
        store.insert("sources", [{
            "source_id": ALIAS_SOURCE_ID, "title": "Place-name aliases for jurisdiction matching",
            "custodian": "research-suite-core", "licence_class": "public", "limitations": _load()["source"]}])
    known = store.keys("jurisdictions", "jurisdiction_id")
    present = {(r["alias"], r["language"]) for r in store.rows("jurisdiction_aliases")}
    rows, seen = [], set(present)
    for alias, code in PlaceMatcher().entries:
        key = (alias, "en" if _is_latin(alias) else "zh-Hans")
        if code in known and key not in seen:
            seen.add(key)
            rows.append({"alias": alias, "language": key[1], "jurisdiction_id": code, "source_id": ALIAS_SOURCE_ID})
    if rows:
        store.insert("jurisdiction_aliases", rows)
    return len(rows)
