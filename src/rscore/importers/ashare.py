"""Import an A-share Company Intelligence release into the shared store (roadmap Phase 3).

The importer reads a release folder (``manifest.json`` and ``csv/``), never the scraper's working
database. It follows the International Tax Network Lab's import note (``docs/ASHARE_IMPORT_NOTE.md``):

* natural persons are excluded, and their names are never written to the store or to any report;
* only direct stakes are stored (the Lab derives indirect holdings);
* places are mapped to jurisdiction codes by ``rscore.places``; anything it cannot place is sent to
  review with a suggestion, never guessed;
* every row keeps its provenance: a source record per disclosure document and page.

Rows that look misparsed are rejected with a reason rather than repaired: a stake outside (0, 100] per
cent, a shareholder type glued onto the name (a sign the table's columns were shifted), or top-ten
stakes summing above 100 per cent.

See ``docs/importers/ashare.md`` for the field mapping.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rscore import jurisdictions, places
from rscore.store import Store

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

#: Shareholder types as printed in annual-report shareholder tables.
TYPE_TOKENS = ("境内非国有法人", "境内一般法人", "境内自然人", "境外自然人", "境外法人", "国有法人", "国有股东", "国家",
               "国有股", "境内法人", "其他")
DOMESTIC_TYPES = ("境内", "国有", "国家")
PERSON_TYPES = ("自然人", "PERSON", "NATURAL")
PSEUDONYM = re.compile(r"^P[0-9A-F]{12}$")
_ORG_WORDS = re.compile(r"公司|集团|银行|基金|计划|信托|证券|保险|资产|合伙|中心|委员会|政府|国资|财政|大学|学院|研究|协会|"
                        r"商会|工会|事务所|产品|账户|专户|组合|企业|厂$|局$|部$|社$|LIMITED|LTD|INC|CORP|LLC|GMBH|PLC|"
                        r"FUND|TRUST|BANK|HOLDING|CAPITAL|PARTNERS|株式会社", re.I)
LICENCE_CLASS = {"PUBLIC_DISCLOSURE": "public_attribution", "PUBLIC_FEED": "public_attribution",
                 "DERIVED": "public_attribution", "MANUAL": "public_attribution",
                 "LICENSED": "licensed_no_redistribution"}
SUM_TOLERANCE = 0.5  # percentage points: rounding in printed tables
AGREEMENT = 0.01     # revenue candidates for one company and year must agree within 1%
MIN_REVENUE = 1e6    # CNY: below this, a listed group's annual revenue is a parsing error


# ------------------------------------------------------------------ options and report
@dataclass
class Options:
    companies: tuple[str, ...] = ()           # security codes; empty means all
    overrides: dict[str, str] = field(default_factory=dict)  # place or holder name -> jurisdiction code
    accept_suggestions: bool = False          # take name-based jurisdiction suggestions as given
    assume_consolidated: bool = False         # treat revenue with no stated scope as consolidated
    min_confidence: float = 0.0


@dataclass
class Review:
    name: str
    status: str
    suggestion: str
    rows: int = 0


@dataclass
class ImportReport:
    release: str = ""
    imported: Counter = field(default_factory=Counter)
    rejected: Counter = field(default_factory=Counter)      # (table, reason) -> rows
    rejected_rows: list[tuple[str, str, str]] = field(default_factory=list)  # table, release row id, reason
    review: dict[str, Review] = field(default_factory=dict)
    revenue_review: list[tuple[str, str, str]] = field(default_factory=list)  # security code, year, candidates
    notes: list[str] = field(default_factory=list)
    unmasked_person_names: int = 0

    def reject(self, table: str, row_id: str, reason: str) -> None:
        self.rejected[(table, reason)] += 1
        self.rejected_rows.append((table, row_id, reason))

    def to_review(self, name: str, status: str, suggestion: str | None) -> None:
        r = self.review.setdefault(name, Review(name, status, suggestion or ""))
        r.rows += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "release": self.release,
            "imported": dict(self.imported),
            "rejected": [{"table": t, "reason": r, "rows": n} for (t, r), n in sorted(self.rejected.items())],
            "review_jurisdictions": len(self.review),
            "review_revenue": len(self.revenue_review),
            "unmasked_person_names": self.unmasked_person_names,
            "notes": self.notes,
        }


# ------------------------------------------------------------------ helpers
def _h(text: str, n: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def _num(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    try:
        x = float(value)
    except ValueError:
        return None
    return x if x == x else None


def _date(value: str | None) -> str | None:
    if value and re.match(r"^\d{4}-\d{2}-\d{2}", value):
        return value[:10]
    return None


def norm_name(name: str) -> str:
    return re.sub(r"\s+", "", name or "").replace("（", "(").replace("）", ")")


def is_natural_person(name: str, *natures: str | None) -> bool:
    """Precautionary: true where a stated type says so, the name is a pseudonym, a person type is glued
    onto the name, or the name looks like a personal name (2 to 5 Chinese characters, no organisation word)."""
    nat = " ".join(n for n in natures if n)
    if any(t in nat.upper() or t in nat for t in PERSON_TYPES):
        return True
    if nat and ("法人" in nat or "国有" in nat):
        return False
    n = norm_name(name)
    if PSEUDONYM.match(n) or "自然人" in n:
        return True
    if _ORG_WORDS.search(n):
        return False
    return bool(re.fullmatch(r"[一-鿿·]{2,5}", n))


def glued_type(name: str) -> str | None:
    """A shareholder type printed onto the end of the name: the table's columns were shifted."""
    n = norm_name(name)
    for token in TYPE_TOKENS:
        if n.endswith(token) and len(n) > len(token):
            return token
    return None


def _read_csv(folder: Path, table: str) -> list[dict[str, str]]:
    path = folder / "csv" / f"{table}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_overrides(path: Path) -> dict[str, str]:
    """A CSV with columns ``name`` and ``jurisdiction_id`` (the review file, once filled in)."""
    out = {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            code = (row.get("jurisdiction_id") or "").strip()
            if row.get("name") and code:
                out[row["name"].strip()] = code
    return out


# ------------------------------------------------------------------ importer
class _Importer:
    def __init__(self, store: Store, folder: Path, options: Options):
        self.store, self.folder, self.opt = store, folder, options
        self.report = ImportReport()
        self.matcher = places.PlaceMatcher(options.overrides)
        self.sources: dict[str, dict] = {}
        self.entities: dict[str, dict] = {}
        self.ownership: dict[str, dict] = {}
        self.financials: dict[tuple[str, str], tuple[float, dict]] = {}
        self.companies: dict[str, dict] = {}
        self.known_jurisdictions = store.keys("jurisdictions", "jurisdiction_id")

    # -------------------------------------------------------------- setup
    def read_manifest(self) -> None:
        path = self.folder / "manifest.json"
        if not path.exists():
            raise FileNotFoundError(f"{self.folder} has no manifest.json; is it an A-share release folder?")
        m = json.loads(path.read_text(encoding="utf-8"))
        self.manifest = m
        self.fp = (m.get("database_fingerprint") or _h(m.get("name", "")))[:8]
        self.report.release = m.get("name", self.folder.name)
        sw = m.get("software", {})
        self.release_source = f"ashare:{self.fp}:release"
        self.citation = m.get("citation", "")
        self.sources[self.release_source] = {
            "source_id": self.release_source,
            "title": f"A-share Company Intelligence release {self.report.release}",
            "custodian": "A-share Company Intelligence (author's dataset release)",
            "retrieval_date": _date(m.get("created_utc")),
            "licence_class": "public_attribution",
            "licence_terms": "Derived from public disclosures; see the release manifest",
            "coverage": f"{m.get('row_counts', {}).get('companies', '?')} companies",
            "limitations": "Heuristic extraction; see the release's quality report",
            "oscola_citation": self.citation or None,
            "content_sha256": m.get("database_fingerprint"),
            "extraction_method": f"{sw.get('name', 'A-share Company Intelligence')} {sw.get('version', '')}".strip(),
        }
        if not m.get("pseudonymisation", {}).get("applied"):
            self.report.notes.append("The release is not pseudonymised; natural persons are still excluded on import.")
        for c in _read_csv(self.folder, "companies"):
            self.companies[c["id"]] = c

    def wanted(self, company_id: str) -> bool:
        if not self.opt.companies:
            return company_id in self.companies
        c = self.companies.get(company_id)
        return bool(c) and c["security_code"] in self.opt.companies

    # -------------------------------------------------------------- records
    def doc_source(self, row: dict[str, str], licence: str = "PUBLIC_DISCLOSURE") -> str:
        url = row.get("source_document") or ""
        page = (row.get("source_page") or "").split(".")[0]
        disclosure = (row.get("disclosure_id") or "").split(".")[0]
        if not url and not disclosure:
            return self.release_source
        ident = _h(url) if url else f"d{disclosure}"
        key = f"ashare:{self.fp}:doc:{ident}" + (f":p{page}" if page else "")
        if key not in self.sources:
            method = "; ".join(x for x in (row.get("extraction_method"),
                                           f"confidence {row['confidence']}" if row.get("confidence") else None,
                                           row.get("validation_status")) if x)
            self.sources[key] = {
                "source_id": key,
                "title": f"{row.get('source') or 'Disclosure'} document"
                         + (f" (release disclosure id {disclosure})" if disclosure else "")
                         + (f", page {page}" if page else ""),
                "custodian": row.get("source") or None,
                "url": url or None,
                "retrieval_date": _date(row.get("retrieved_at")),
                "licence_class": LICENCE_CLASS.get(licence, "public_attribution"),
                "licence_terms": "Public disclosure",
                "limitations": f"Extracted by A-share Company Intelligence; via release {self.report.release}",
                "extraction_method": method or None,
            }
        return key

    def company_entity(self, company_id: str, source_id: str) -> str:
        c = self.companies[company_id]
        eid = f"ashare:co:{c['security_code']}"
        if eid not in self.entities:
            name = c.get("legal_name_cn") or c.get("short_name_cn") or c["security_code"]
            self.entities[eid] = {
                "entity_id": eid, "reported_name": name, "jurisdiction_id": "CHN",
                "entity_type": "listed_company",
                "entity_type_rule": f"listed on {c.get('exchange')} ({c.get('board')}); security code {c['security_code']}",
                "is_natural_person": False, "valid_from": _date(c.get("listing_date")), "source_id": self.release_source,
            }
        return eid

    def org_entity(self, name: str, jurisdiction: str, entity_type: str, rule: str, source_id: str) -> str:
        eid = f"ashare:org:{_h(norm_name(name))}"
        if eid not in self.entities:
            self.entities[eid] = {
                "entity_id": eid, "reported_name": norm_name(name)[:200], "jurisdiction_id": jurisdiction,
                "entity_type": entity_type, "entity_type_rule": rule, "is_natural_person": False,
                "source_id": source_id,
            }
        return eid

    def holder_jurisdiction(self, name: str, holder_type: str | None) -> tuple[str | None, str | None]:
        """(jurisdiction, suggestion) for a holder named in a shareholder or control table. The jurisdiction
        is None when it is not stated; the suggestion, matched from the name, is then offered for review."""
        n = norm_name(name)
        if n in self.matcher.overrides:
            return self.matcher.overrides[n], None
        if holder_type and any(t in holder_type for t in DOMESTIC_TYPES):
            return "CHN", None
        guess = self.matcher.match(n)
        if self.opt.accept_suggestions and guess.status == "matched":
            return guess.code, None
        return None, guess.code

    def resolve_holders(self, table: str, row_id: str, holders: list[tuple[str, str | None]]) -> list[str] | None:
        """Jurisdictions for every holder in a row, or None (the row is rejected once and the names reviewed)."""
        codes, missing = [], []
        for name, holder_type in holders:
            code, suggestion = self.holder_jurisdiction(name, holder_type)
            if code is None:
                missing.append((name, suggestion))
            codes.append(code)
        if missing:
            for name, suggestion in missing:
                self.report.to_review(norm_name(name), "holder jurisdiction not stated", suggestion)
            self.report.reject(table, row_id, "holder_jurisdiction_needs_review")
            return None
        if any(c not in self.known_jurisdictions for c in codes):
            self.report.reject(table, row_id, "unknown_jurisdiction_code")
            return None
        return codes

    def resolve_place(self, row: dict[str, str], table: str) -> str | None:
        for column in ("registered_place", "principal_place"):
            text = row.get(column)
            if not text or not text.strip():
                continue
            m = self.matcher.match(text)
            if m.code:
                return m.code
            self.report.to_review(places.normalise(text), f"place {m.status}", "/".join(m.candidates))
            self.report.reject(table, row["id"], f"place_{m.status}")
            return None
        self.report.reject(table, row["id"], "place_missing")
        return None

    @staticmethod
    def shifted(row: dict[str, str]) -> bool:
        name = norm_name(row.get("shareholder_name") or "")
        if not (row.get("shareholder_type") or "").strip() and glued_type(name):
            return True
        # Another column's value inside the name, such as a pseudonymised co-holder after a separator.
        return any(PSEUDONYM.match(part) for part in re.split(r"[、,，;；/]", name)[1:])

    def low_confidence(self, row: dict[str, str]) -> bool:
        conf = _num(row.get("confidence"))
        return (conf is not None and conf < self.opt.min_confidence) or row.get("validation_status") == "REJECTED"

    # -------------------------------------------------------------- tables
    def shareholders(self) -> None:
        """Shareholder tables are judged as tables: if any row of a company's table for a date shows shifted
        columns (a type glued onto a name, or another field's pseudonym inside a name), every row of that
        table is rejected, since the shift misplaces the stakes of the whole table."""
        table = "ownership_observations"
        rows_by_table: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in _read_csv(self.folder, table):
            if self.wanted(r["company_id"]):
                rows_by_table[(r["company_id"], r.get("observation_date") or "")].append(r)
        groups: dict[tuple[str, str], list[tuple[dict, float]]] = defaultdict(list)
        for key, rows in rows_by_table.items():
            shifted = any(self.shifted(r) for r in rows)
            for r in rows:
                name = r.get("shareholder_name") or ""
                if is_natural_person(name, r.get("shareholder_type"), r.get("shareholder_nature")):
                    if not PSEUDONYM.match(norm_name(name)):
                        self.report.unmasked_person_names += 1
                    self.report.reject(table, r["id"], "natural_person_excluded")
                    continue
                if shifted:
                    self.report.reject(table, r["id"], "table_columns_shifted")
                    continue
                pct = _num(r.get("ownership_pct"))
                if pct is None:
                    self.report.reject(table, r["id"], "stake_missing")
                    continue
                if not 0 < pct <= 100:
                    self.report.reject(table, r["id"], "stake_outside_0_100")
                    continue
                if self.low_confidence(r):
                    self.report.reject(table, r["id"], "below_min_confidence")
                    continue
                groups[key].append((r, pct))
        for (company_id, date), rows in groups.items():
            total = sum(p for _, p in rows)
            if total > 100 + SUM_TOLERANCE:
                for r, _ in rows:
                    self.report.reject(table, r["id"], "stakes_sum_over_100")
                continue
            for r, pct in rows:
                holder_type = r.get("shareholder_type") or r.get("shareholder_nature")
                codes = self.resolve_holders(table, r["id"], [(r["shareholder_name"], holder_type)])
                if codes is None:
                    continue
                jur = codes[0]
                src = self.doc_source(r)
                held = self.company_entity(company_id, src)
                holder = self.org_entity(r["shareholder_name"], jur, "shareholder",
                                         f"shareholder type: {holder_type or 'not stated'}", src)
                self.add_relation(f"ashare:{self.fp}:own:{r['id']}", holder, held, "equity", pct / 100,
                                  _date(date), src)

    def subsidiaries(self) -> None:
        table = "subsidiary_observations"
        for r in _read_csv(self.folder, table):
            if not self.wanted(r["company_id"]):
                continue
            direct, indirect, total = (_num(r.get(c)) for c in ("direct_pct", "indirect_pct", "total_pct"))
            pct = direct if direct is not None else (total if not indirect and total is not None else None)
            if pct is None:
                self.report.reject(table, r["id"], "no_direct_stake")
                continue
            if pct == 0 and indirect:
                self.report.reject(table, r["id"], "indirect_only")
                continue
            if not 0 < pct <= 100:
                self.report.reject(table, r["id"], "stake_outside_0_100")
                continue
            if self.low_confidence(r):
                self.report.reject(table, r["id"], "below_min_confidence")
                continue
            jur = self.resolve_place(r, table)
            if jur is None:
                continue
            src = self.doc_source(r)
            parent = self.company_entity(r["company_id"], src)
            kind = (r.get("relationship") or "subsidiary").strip().lower() or "subsidiary"
            place = r.get("registered_place") or r.get("principal_place") or ""
            child = self.org_entity(r["entity_name"], jur, kind, f"place as disclosed: {places.normalise(place)}", src)
            self.add_relation(f"ashare:{self.fp}:sub:{r['id']}", parent, child, "equity", pct / 100,
                              _date(r.get("observation_date")), src)

    def control(self) -> None:
        table = "control_observations"
        for r in _read_csv(self.folder, table):
            if not self.wanted(r["company_id"]):
                continue
            name = (r.get("controlling_shareholder") or "").strip()
            if r.get("actual_controller"):
                self.report.imported["actual_controllers_not_stored"] += 1
            if not name:
                continue
            if is_natural_person(name, r.get("controlling_nature")):
                self.report.reject(table, r["id"], "natural_person_excluded")
                continue
            codes = self.resolve_holders(table, r["id"], [(name, r.get("controlling_nature"))])
            if codes is None:
                continue
            jur = codes[0]
            src = self.doc_source(r)
            held = self.company_entity(r["company_id"], src)
            holder = self.org_entity(name, jur, "controlling_shareholder",
                                     f"controlling shareholder; nature: {r.get('controlling_nature') or 'not stated'}", src)
            self.add_relation(f"ashare:{self.fp}:cob:{r['id']}", holder, held, "control", None,
                              _date(r.get("observation_date")), src)

    def control_edges(self) -> None:
        table = "control_edges"
        for r in _read_csv(self.folder, table):
            if not self.wanted(r["company_id"]):
                continue
            parent, child = r.get("parent_name") or "", r.get("child_name") or ""
            if is_natural_person(parent) or is_natural_person(child):
                self.report.reject(table, r["id"], "natural_person_excluded")
                continue
            pct = _num(r.get("pct"))
            if pct is not None and not 0 < pct <= 100:
                self.report.reject(table, r["id"], "stake_outside_0_100")
                continue
            codes = self.resolve_holders(table, r["id"], [(parent, None), (child, None)])
            if codes is None:
                continue
            src = self.release_source
            a = self.org_entity(parent, codes[0], "chain_member", "named in a disclosed control chain", src)
            b = self.org_entity(child, codes[1], "chain_member", "named in a disclosed control chain", src)
            self.add_relation(f"ashare:{self.fp}:ctl:{r['id']}", a, b, "equity" if pct else "control",
                              pct / 100 if pct else None, _date(r.get("observation_date")), src)

    def revenue(self) -> None:
        """Annual consolidated revenue. A release may hold several candidates for one company and year (from
        different parsers or pages). They are imported only if they agree within ``AGREEMENT``; otherwise all
        are rejected, since the disagreement usually means a scale or table error that choosing by confidence
        would hide."""
        table = "financial_facts"
        candidates: dict[tuple[str, str], list[tuple[dict, float, str]]] = defaultdict(list)
        for r in _read_csv(self.folder, table):
            if r.get("metric") != "revenue" or r.get("period_type") != "FY" or not self.wanted(r["company_id"]):
                continue
            value = _num(r.get("value"))
            if value is None or value < 0:
                self.report.reject(table, r["id"], "revenue_missing_or_negative")
                continue
            scope = r.get("consolidation_scope") or ""
            if scope.startswith("DIM:"):
                continue  # a segment or other dimension, not the entity's total
            if scope == "CONSOLIDATED_DEFAULT" or (not scope and self.opt.assume_consolidated):
                consolidation = "consolidated"
            else:
                self.report.reject(table, r["id"], "consolidation_scope_not_stated")
                continue
            if self.low_confidence(r):
                self.report.reject(table, r["id"], "below_min_confidence")
                continue
            if value < MIN_REVENUE:
                self.report.reject(table, r["id"], "revenue_implausibly_small")
                continue
            candidates[(r["company_id"], (r.get("reporting_period") or "")[:4])].append((r, value, consolidation))
        for (company_id, period), rows in candidates.items():
            values = [v for _, v, _ in rows]
            if max(values) > min(values) * (1 + AGREEMENT):
                for r, _, _ in rows:
                    self.report.reject(table, r["id"], "revenue_candidates_disagree")
                self.report.revenue_review.append((self.companies[company_id]["security_code"], period,
                                                   " / ".join(f"{v:,.0f}" for v in sorted(set(values)))))
                continue
            r, value, consolidation = max(rows, key=lambda x: _num(x[0].get("confidence")) or 0.0)
            src = self.doc_source(r)
            eid = self.company_entity(company_id, src)
            self.financials[(eid, period)] = (0.0, {
                "entity_id": eid, "period": period, "operating_revenue": value,
                "currency": r.get("currency") or "CNY", "consolidation": consolidation, "source_id": src})
        if self.opt.assume_consolidated:
            self.report.notes.append("Revenue with no stated consolidation scope was treated as consolidated "
                                     "(--assume-consolidated).")
        if self.financials:
            self.report.notes.append("Revenue resting on a single candidate cannot be cross-checked here; treat it as "
                                     "unverified until reviewed in A-share Company Intelligence.")

    def add_relation(self, rid: str, holder: str, held: str, rtype: str, fraction: float | None,
                     valid_from: str | None, src: str) -> None:
        if valid_from is None:
            self.report.reject("ownership", rid, "observation_date_missing")
            return
        self.ownership[rid] = {"relation_id": rid, "holder_id": holder, "held_id": held, "relation_type": rtype,
                               "fraction": fraction, "direct": True, "valid_from": valid_from, "source_id": src}

    # -------------------------------------------------------------- write
    def write(self) -> None:
        used_sources = {r["source_id"] for r in self.entities.values()} | {r["source_id"] for r in self.ownership.values()} \
            | {row["source_id"] for _, row in self.financials.values()} | {self.release_source}
        sources = [s for k, s in self.sources.items() if k in used_sources]
        actual = self.report.imported.pop("actual_controllers_not_stored", 0)
        if actual:
            self.report.notes.append(f"{actual} actual controller(s) not stored: they control indirectly, and only "
                                     "direct relations are stored.")
        for table, rows in (("sources", sources), ("entities", list(self.entities.values())),
                            ("ownership", list(self.ownership.values())),
                            ("entity_financials", [row for _, row in self.financials.values()])):
            if rows:
                self.store.insert(table, rows, replace=True)
            self.report.imported[table] = len(rows)
        if self.opt.accept_suggestions:
            self.report.notes.append("Holder jurisdictions suggested from names were accepted (--accept-suggestions).")
        if self.report.unmasked_person_names:
            self.report.notes.append(
                f"{self.report.unmasked_person_names} natural-person name(s) in the release were not pseudonymised. "
                "They were excluded here and are not repeated in any report, but the release itself should not be "
                "shared until it is regenerated.")


def import_release(store: Store, folder: str | Path, options: Options | None = None) -> ImportReport:
    """Import a release folder into the store and return the report. Validation errors raise and write nothing
    for the failing table."""
    jurisdictions.seed(store)
    places.seed_aliases(store)
    imp = _Importer(store, Path(folder), options or Options())
    imp.read_manifest()
    imp.shareholders()
    imp.subsidiaries()
    imp.control()
    imp.control_edges()
    imp.revenue()
    imp.write()
    return imp.report


# ------------------------------------------------------------------ report files
def write_report(report: ImportReport, directory: str | Path) -> list[Path]:
    """Write import_report.json, import_report.md, rejected_rows.csv and review_jurisdictions.csv.
    No file contains the name of a natural person: rejected rows are listed by release row id only."""
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    paths = [out / "import_report.json", out / "import_report.md", out / "rejected_rows.csv",
             out / "review_jurisdictions.csv", out / "review_revenue.csv"]
    paths[0].write_text(json.dumps(report.as_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [f"# Import of {report.release}", "", "## Imported", "", "| Table | Rows |", "| --- | ---: |"]
    lines += [f"| {t} | {n} |" for t, n in report.imported.items()]
    lines += ["", "## Rejected", "", "| Release table | Reason | Rows |", "| --- | --- | ---: |"]
    lines += [f"| {t} | {r.replace('_', ' ')} | {n} |" for (t, r), n in sorted(report.rejected.items())] or ["| none | | |"]
    lines += ["", "## Review", "",
              f"- {len(report.review)} name(s) or place(s) need a jurisdiction: see `review_jurisdictions.csv`. Fill in "
              "`jurisdiction_id` and pass the file back with `--overrides`.",
              f"- {len(report.revenue_review)} company-year(s) have revenue candidates that disagree: see "
              "`review_revenue.csv`. Resolve them in A-share Company Intelligence's review queue, then make a new release."]
    if report.notes:
        lines += ["", "## Notes", ""] + [f"- {n}" for n in report.notes]
    paths[1].write_text("\n".join(lines) + "\n", encoding="utf-8")
    with paths[2].open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["release_table", "release_row_id", "reason"])
        w.writerows(report.rejected_rows)
    with paths[3].open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["name", "status", "suggested_jurisdiction", "rows", "jurisdiction_id"])
        for r in sorted(report.review.values(), key=lambda r: (-r.rows, r.name)):
            w.writerow([r.name, r.status, r.suggestion, r.rows, ""])
    with paths[4].open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["security_code", "year", "candidates_cny"])
        w.writerows(report.revenue_review)
    return paths

