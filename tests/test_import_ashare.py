import csv
import os
import sys

import pytest
from fake_release import PERSON, build

from rscore import export, places
from rscore.__main__ import main as cli
from rscore.importers import ashare
from rscore.store import Store


@pytest.fixture
def release(tmp_path):
    return build(tmp_path / "release")


@pytest.fixture
def imported(tmp_path, release):
    store = Store(tmp_path / "p.sqlite")
    report = ashare.import_release(store, release)
    yield store, report
    store.close()


def reasons(report):
    return {(t, r): n for (t, r), n in report.rejected.items()}


# ------------------------------------------------------------------ places
@pytest.mark.parametrize("text,code,status", [
    ("香港", "HKG", "matched"), ("中国香港", "HKG", "matched"), ("开曼群岛", "CYM", "matched"),
    ("British Virgin Islands", "VGB", "matched"), ("广东省深圳市", "CHN", "matched"), ("内蒙古", "CHN", "matched"),
    ("印度尼西亚", "IDN", "matched"), ("New Jersey, USA", "USA", "matched"), ("Jersey", "JEY", "matched"),
    ("维尔京群岛", None, "unmatched"), ("欧洲", None, "unmatched"), ("", None, "empty"),
    ("香港及新加坡", None, "ambiguous"), ("Hongkong", None, "unmatched"),
])
def test_place_matching(text, code, status):
    m = places.PlaceMatcher().match(text)
    assert (m.code, m.status) == (code, status)


def test_place_override_wins():
    assert places.PlaceMatcher({"维尔京群岛": "VGB"}).match("维尔京群岛").code == "VGB"


def test_aliases_seeded(store):
    from rscore import jurisdictions
    jurisdictions.seed(store)
    n = places.seed_aliases(store)
    assert n > 200 and places.seed_aliases(store) == 0


# ------------------------------------------------------------------ import
def test_group_imported(imported):
    store, report = imported
    own = {r["relation_id"].split(":")[-2] + r["relation_id"].split(":")[-1]: r for r in store.rows("ownership")}
    ents = {r["entity_id"]: r for r in store.rows("entities")}
    # The controlling shareholder (domestic type, so CHN) holds 51.2% of the listed company.
    assert own["own1"]["fraction"] == pytest.approx(0.512) and own["own1"]["held_id"] == "ashare:co:000999"
    # Subsidiaries: Hong Kong, Cayman, Shenzhen.
    subs = {ents[r["held_id"]]["jurisdiction_id"]: r["fraction"] for k, r in own.items() if k.startswith("sub")}
    assert subs == {"HKG": 1.0, "CYM": 1.0, "CHN": 0.7}
    # Control relation without a fraction; revenue in yuan, consolidated.
    assert own["cob1"]["relation_type"] == "control" and own["cob1"]["fraction"] is None
    fin = store.rows("entity_financials")
    assert len(fin) == 1 and fin[0]["operating_revenue"] == 1.5e10 and fin[0]["period"] == "2025"
    assert ents["ashare:co:000999"]["reported_name"] == "示例股份有限公司"


def test_rejections(imported):
    _, report = imported
    r = reasons(report)
    assert r[("ownership_observations", "natural_person_excluded")] == 1
    assert r[("ownership_observations", "table_columns_shifted")] == 1
    assert r[("ownership_observations", "stakes_sum_over_100")] == 2
    assert r[("ownership_observations", "stake_outside_0_100")] == 1
    assert r[("ownership_observations", "holder_jurisdiction_needs_review")] == 1
    assert r[("subsidiary_observations", "indirect_only")] == 1
    assert r[("subsidiary_observations", "place_unmatched")] == 2
    assert r[("financial_facts", "consolidation_scope_not_stated")] == 3
    review = {v.name: v for v in report.review.values()}
    assert review["香港中央结算有限公司"].suggestion == "HKG"
    assert "欧洲" in review and "维尔京群岛" in review


def test_a_shift_rejects_the_whole_table(tmp_path):
    from fake_release import TABLES, _sh
    import copy
    import fake_release
    saved = copy.deepcopy(TABLES["ownership_observations"])
    try:
        TABLES["ownership_observations"][:] = [
            _sh(1, 1, "甲基金有限公司、P87A265376617", "", 46.0),      # pseudonym of another field inside the name
            _sh(2, 1, "乙投资有限公司", "境内非国有法人", 10.0),
        ]
        release = fake_release.build(tmp_path / "rel")
        with Store(tmp_path / "p.sqlite") as store:
            report = ashare.import_release(store, release)
        assert reasons(report)[("ownership_observations", "table_columns_shifted")] == 2
    finally:
        TABLES["ownership_observations"][:] = saved


def test_every_relation_traces_to_a_document(imported):
    store, _ = imported
    sources = {s["source_id"]: s for s in store.rows("sources")}
    for r in store.rows("ownership"):
        s = sources[r["source_id"]]
        assert s["url"] or "disclosure id" in s["title"], r["relation_id"]
        assert "page" in s["title"]


def test_store_is_valid_and_reimport_is_stable(tmp_path, release):
    with Store(tmp_path / "p.sqlite") as store:
        ashare.import_release(store, release)
        before = {t: store.count(t) for t in ("entities", "ownership", "sources")}
        ashare.import_release(store, release)
        assert {t: store.count(t) for t in before} == before
        assert store.validate().ok


def test_overrides_and_suggestions(tmp_path, release):
    with Store(tmp_path / "a.sqlite") as store:
        report = ashare.import_release(store, release, ashare.Options(overrides={"香港中央结算有限公司": "HKG",
                                                                              "欧洲": "DEU"}))
        r = reasons(report)
        assert ("ownership_observations", "holder_jurisdiction_needs_review") not in r
        assert r[("subsidiary_observations", "place_unmatched")] == 1
    with Store(tmp_path / "b.sqlite") as store:
        report = ashare.import_release(store, release, ashare.Options(accept_suggestions=True))
        assert ("ownership_observations", "holder_jurisdiction_needs_review") not in reasons(report)
        assert any("accepted" in n for n in report.notes)


def test_company_filter_and_assumptions(tmp_path, release):
    with Store(tmp_path / "p.sqlite") as store:
        report = ashare.import_release(store, release, ashare.Options(companies=("600998",),
                                                                      assume_consolidated=True))
        # The three candidates disagree (one is 1,000 times too small, one is implausibly small): none imported.
        assert store.count("entity_financials") == 0
        r = reasons(report)
        assert r[("financial_facts", "revenue_candidates_disagree")] == 2
        assert r[("financial_facts", "revenue_implausibly_small")] == 1
        assert report.revenue_review == [("600998", "2025", "3,000,000 / 3,000,000,000")]
        assert any("assume-consolidated" in n for n in report.notes)


def test_no_personal_name_leaves_the_importer(tmp_path, release):
    with Store(tmp_path / "p.sqlite") as store:
        report = ashare.import_release(store, release)
        paths = ashare.write_report(report, tmp_path / "report")
        dump = "\n".join("".join(str(v) for v in row.values()) for t in ("entities", "sources") for row in store.rows(t))
    assert PERSON not in dump
    for path in paths:
        assert PERSON not in path.read_text(encoding="utf-8-sig"), path.name


def test_unmasked_names_counted(tmp_path, release):
    with Store(tmp_path / "p.sqlite") as store:
        report = ashare.import_release(store, release)
    assert report.unmasked_person_names == 1
    assert any("should not be shared" in n for n in report.notes)


def test_review_file_round_trip(tmp_path, release):
    with Store(tmp_path / "p.sqlite") as store:
        report = ashare.import_release(store, release)
        ashare.write_report(report, tmp_path / "report")
    path = tmp_path / "report" / "review_jurisdictions.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    for row in rows:
        row["jurisdiction_id"] = row["suggested_jurisdiction"] or "VGB"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    overrides = ashare.read_overrides(path)
    assert overrides["香港中央结算有限公司"] == "HKG"
    with Store(tmp_path / "q.sqlite") as store:
        report = ashare.import_release(store, release, ashare.Options(overrides=overrides))
    assert not any(r.startswith("place_") or r.startswith("holder_") for (_, r) in report.rejected)


def test_cli(tmp_path, release, capsys):
    code = cli(["--store", str(tmp_path / "p.sqlite"), "import-ashare", str(release),
                "--report", str(tmp_path / "rep")])
    assert code == 0 and "## Rejected" in capsys.readouterr().out
    assert cli(["--store", str(tmp_path / "p.sqlite"), "validate"]) == 0
    assert cli(["--store", str(tmp_path / "p.sqlite"), "export-lab", str(tmp_path / "lab")]) == 0
    assert cli(["--store", str(tmp_path / "p.sqlite"), "import-ashare", str(tmp_path / "nowhere")]) == 2


LAB_SRC = os.environ.get("TAXNETLAB_SRC")


@pytest.mark.skipif(not LAB_SRC, reason="set TAXNETLAB_SRC to the Lab's src folder to run this check")
def test_lab_accepts_the_imported_group(tmp_path, release):
    """Phase 3 gate on example data: the group loads in the Lab, and the Lab's own graph of it has the group's
    edges."""
    sys.path.insert(0, LAB_SRC)
    try:
        from taxnetlab.datasets import Dataset
    finally:
        sys.path.remove(LAB_SRC)
    with Store(tmp_path / "p.sqlite") as store:
        ashare.import_release(store, release)
        export.lab_dataset(store, tmp_path / "lab")
    texts = {p.stem: p.read_text(encoding="utf-8") for p in (tmp_path / "lab").glob("*.csv")}
    dataset, report = Dataset.from_csv_texts("A-share example group", texts)
    assert dataset is not None, report
    assert dataset.counts()["ownership"] == 5 and dataset.counts()["entity_financials"] == 1
