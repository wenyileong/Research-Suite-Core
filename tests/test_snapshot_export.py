import csv
import json
import os
import sys
from pathlib import Path

import pytest
from conftest import entity, owns

from rscore import export, jurisdictions, snapshot
from rscore.store import Store


def fill(store, order):
    jurisdictions.seed(store)
    store.insert("sources", [{"source_id": "test_src", "title": "Test", "licence_class": "public"}])
    ents = [entity("a"), entity("b", "HKG"), entity("c", "CYM")]
    store.insert("entities", ents if order else list(reversed(ents)))
    store.insert("ownership", [owns("r1", "a", "b", 0.75), owns("r2", "b", "c")])


def test_snapshot_id_ignores_insertion_order(tmp_path):
    with Store(tmp_path / "one.sqlite") as s1, Store(tmp_path / "two.sqlite") as s2:
        fill(s1, True)
        fill(s2, False)
        assert snapshot.snapshot_id(s1) == snapshot.snapshot_id(s2)


def test_snapshot_id_changes_with_content(seeded):
    seeded.insert("entities", [entity("a")])
    before = snapshot.snapshot_id(seeded)
    seeded.insert("entities", [entity("a", reported_name="Other")], replace=True)
    assert snapshot.snapshot_id(seeded) != before


def test_empty_tables_do_not_enter_the_hash(seeded):
    assert set(snapshot.table_hashes(seeded)) == {"sources", "jurisdictions"}


def test_canonical_form(seeded):
    seeded.insert("entities", [entity("a"), entity("b")])
    seeded.insert("ownership", [owns("r1", "a", "b", 0.1)])
    text = snapshot.table_csv(seeded, "ownership")
    assert text.endswith("\n") and "\r" not in text
    row = next(csv.DictReader(text.splitlines()))
    assert row["fraction"] == "0.1" and row["direct"] == "true" and row["valid_to"] == ""


def test_export_and_verify(seeded, tmp_path):
    seeded.insert("entities", [entity("a")])
    path = snapshot.export(seeded, tmp_path / "snaps", note="test")
    manifest = json.loads((path / "manifest.json").read_text())
    assert path.name == manifest["snapshot_id"] and manifest["counts"]["entities"] == 1
    assert snapshot.verify(path) == []
    assert seeded.count("snapshots") == 1
    (path / "entities.csv").write_text("tampered\n", encoding="utf-8")
    assert snapshot.verify(path) == ["entities.csv has changed since export"]


def test_lab_export_has_exact_lab_columns(tmp_path):
    with Store(tmp_path / "p.sqlite") as s:
        fill(s, True)
        written = export.lab_dataset(s, tmp_path / "lab")
    names = {p.name for p in written}
    assert names == {"sources.csv", "jurisdictions.csv", "entities.csv", "ownership.csv"}
    header = (tmp_path / "lab" / "jurisdictions.csv").read_text().splitlines()[0]
    assert header == "jurisdiction_id,display_name,iso3,fictional,parent_jurisdiction_id"
    assert "SUP_EU" not in (tmp_path / "lab" / "jurisdictions.csv").read_text()


LAB_SRC = os.environ.get("TAXNETLAB_SRC")


@pytest.mark.skipif(not LAB_SRC, reason="set TAXNETLAB_SRC to the Lab's src folder to run this check")
def test_lab_imports_the_export(tmp_path):
    """Read-only check against the Lab's own importer, run only where a Lab checkout is available."""
    sys.path.insert(0, LAB_SRC)
    try:
        from taxnetlab.canonical import sha256_text
        from taxnetlab.datasets import Dataset
    finally:
        sys.path.remove(LAB_SRC)
    with Store(tmp_path / "p.sqlite") as s:
        fill(s, True)
        export.lab_dataset(s, tmp_path / "lab")
        own_hash = snapshot.table_hashes(s)["ownership"]
    texts = {p.stem: p.read_text(encoding="utf-8") for p in (tmp_path / "lab").glob("*.csv")}
    dataset, report = Dataset.from_csv_texts("rscore export", texts)
    assert dataset is not None, str(report.errors if hasattr(report, "errors") else report)
    assert dataset.counts()["ownership"] == 2
    # The ownership table has no shared-model extensions, so both sides hash it identically.
    assert dataset.table_hashes()["ownership"] == own_hash == sha256_text(texts["ownership"])
