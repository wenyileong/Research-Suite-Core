import pytest

from rscore import jurisdictions
from rscore.store import Store

SRC = {"source_id": "test_src", "title": "Test source", "licence_class": "public"}


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / "project.sqlite") as s:
        yield s


@pytest.fixture
def seeded(store):
    jurisdictions.seed(store)
    store.insert("sources", [SRC])
    return store


def entity(eid, jur="CHN", **kw):
    row = {"entity_id": eid, "reported_name": eid.title(), "jurisdiction_id": jur, "entity_type": "company",
           "is_natural_person": False, "source_id": "test_src"}
    row.update(kw)
    return row


def owns(rid, holder, held, fraction=1.0, **kw):
    row = {"relation_id": rid, "holder_id": holder, "held_id": held, "relation_type": "equity",
           "fraction": fraction, "direct": True, "valid_from": "2024-01-01", "source_id": "test_src"}
    row.update(kw)
    return row
