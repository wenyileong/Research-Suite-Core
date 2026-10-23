import sqlite3

import pytest
from conftest import entity, owns

from rscore import SCHEMA_GENERATION, jurisdictions
from rscore.store import Store, StoreError
from rscore.validation import ValidationError


def test_new_store_records_generation(store):
    assert store.generation == SCHEMA_GENERATION


def test_reopen_keeps_data(tmp_path):
    path = tmp_path / "p.sqlite"
    with Store(path) as s:
        jurisdictions.seed(s)
    with Store(path) as s:
        assert s.count("jurisdictions") == 250


def test_newer_store_is_refused(tmp_path):
    path = tmp_path / "p.sqlite"
    Store(path).close()
    conn = sqlite3.connect(path)
    with conn:
        conn.execute("UPDATE meta SET value = ? WHERE key = 'schema_generation'", (str(SCHEMA_GENERATION + 1),))
    conn.close()
    with pytest.raises(StoreError, match="newer version"):
        Store(path)


def test_insert_and_read_back(seeded):
    seeded.insert("entities", [entity("parent"), entity("sub", "HKG")])
    seeded.insert("ownership", [owns("r1", "parent", "sub", 0.6)])
    rows = seeded.rows("ownership")
    assert rows[0]["fraction"] == 0.6 and rows[0]["direct"] is True


def test_batch_is_all_or_nothing(seeded):
    with pytest.raises(ValidationError):
        seeded.insert("entities", [entity("good"), entity("bad", "XX")])
    assert seeded.count("entities") == 0


@pytest.mark.parametrize("row,message", [
    (entity("p", is_natural_person=True), "natural persons"),
    (entity("p", jurisdiction_id="ZZZ"), "not in jurisdictions"),
    (entity("p", source_id="nowhere"), "not in sources"),
    (entity("p", valid_from="2025-01-01", valid_to="2024-01-01"), "earlier than valid_from"),
    ({**entity("p"), "colour": "red"}, "unknown column"),
    ({k: v for k, v in entity("p").items() if k != "reported_name"}, "reported_name is required"),
])
def test_entity_errors(seeded, row, message):
    with pytest.raises(ValidationError, match=message):
        seeded.insert("entities", [row])


def test_ownership_rules(seeded):
    seeded.insert("entities", [entity("a"), entity("b")])
    report = seeded.insert("ownership", [owns("r0", "a", "a")])
    assert "holds itself" in str(report.warnings[0])
    with pytest.raises(ValidationError, match="only direct relations"):
        seeded.insert("ownership", [owns("r9", "a", "b", direct=False)])
    with pytest.raises(ValidationError, match="requires value_currency"):
        seeded.insert("ownership", [owns("r9", "a", "b", value_amount=100.0)])
    with pytest.raises(ValidationError, match="above the maximum"):
        seeded.insert("ownership", [owns("r1", "a", "b", 1.2)])
    with pytest.raises(ValidationError, match="not in entities"):
        seeded.insert("ownership", [owns("r1", "a", "c")])


def test_duplicates_and_replace(seeded):
    seeded.insert("entities", [entity("a")])
    with pytest.raises(ValidationError, match="already in the store"):
        seeded.insert("entities", [entity("a")])
    with pytest.raises(ValidationError, match="duplicate key in this batch"):
        seeded.insert("entities", [entity("b"), entity("b")])
    seeded.insert("entities", [entity("a", reported_name="Renamed")], replace=True)
    assert seeded.rows("entities")[0]["reported_name"] == "Renamed"


def test_jurisdiction_rules(store):
    with pytest.raises(ValidationError, match="FIC_"):
        store.insert("jurisdictions", [{"jurisdiction_id": "FIC_A", "display_name": "A", "fictional": False}])
    with pytest.raises(ValidationError, match="supranational"):
        store.insert("jurisdictions", [{"jurisdiction_id": "SUP_X", "display_name": "X", "fictional": False,
                                        "kind": "sovereign_state"}])
    with pytest.raises(ValidationError, match="own parent"):
        store.insert("jurisdictions", [{"jurisdiction_id": "FIC_B", "display_name": "B", "fictional": True,
                                        "parent_jurisdiction_id": "FIC_B"}])
    # A parent in the same batch is accepted.
    store.insert("jurisdictions", [
        {"jurisdiction_id": "FIC_P", "display_name": "P", "fictional": True},
        {"jurisdiction_id": "FIC_C", "display_name": "C", "fictional": True, "parent_jurisdiction_id": "FIC_P"},
    ])


def test_validate_clean_store(seeded):
    seeded.insert("entities", [entity("a"), entity("b", "CYM")])
    seeded.insert("ownership", [owns("r1", "a", "b")])
    assert seeded.validate().ok


def test_validate_catches_outside_edits(seeded):
    seeded.insert("entities", [entity("a")])
    with seeded.conn:
        seeded.conn.execute("UPDATE entities SET is_natural_person = 1")
    report = seeded.validate()
    assert not report.ok and "natural persons" in str(report)


def test_bookkeeping_tables_cannot_be_written(store):
    with pytest.raises(KeyError):
        store.insert("meta", [{"key": "x", "value": "y"}])


def test_synthetic_data_stays_on_fictional_jurisdictions(seeded):
    seeded.insert("sources", [{"source_id": "synth", "title": "Generated", "licence_class": "synthetic"}])
    seeded.insert("jurisdictions", [{"jurisdiction_id": "FIC_A", "display_name": "A", "fictional": True}])
    seeded.insert("entities", [entity("x", "FIC_A", source_id="synth")])
    with pytest.raises(ValidationError, match="synthetic record attributed to real jurisdiction 'CHN'"):
        seeded.insert("entities", [entity("y", "CHN", source_id="synth")])


def test_iso3_must_match(store):
    with pytest.raises(ValidationError, match="iso3"):
        store.insert("jurisdictions", [{"jurisdiction_id": "CHN", "display_name": "China", "iso3": "HKG",
                                        "fictional": False}])


def test_group_warnings(seeded):
    seeded.insert("entities", [entity("a"), entity("b"), entity("c")])
    seeded.insert("ownership", [owns("r1", "a", "c", 0.7), owns("r2", "b", "c", 0.6), owns("r3", "c", "a", 0.1)])
    report = seeded.validate()
    text = str(report)
    assert report.ok
    assert "sum to 1.3000" in text
    assert "ownership cycle" in text and "a -> c -> a" in text


def test_replace_a_referenced_row(seeded):
    seeded.insert("entities", [entity("a"), entity("b")])
    seeded.insert("ownership", [owns("r1", "a", "b", 0.5)])
    seeded.insert("entities", [entity("a", reported_name="A renamed")], replace=True)
    assert {r["entity_id"]: r["reported_name"] for r in seeded.rows("entities")}["a"] == "A renamed"
    assert seeded.count("ownership") == 1 and seeded.validate().ok
