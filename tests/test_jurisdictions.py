from rscore import jurisdictions


def test_seed_is_complete_and_idempotent(store):
    assert jurisdictions.seed(store) == 250
    assert jurisdictions.seed(store) == 0
    assert store.count("jurisdictions") == 250


def test_special_cases(store):
    jurisdictions.seed(store)
    rows = {r["jurisdiction_id"]: r for r in store.rows("jurisdictions")}
    assert rows["HKG"]["kind"] == "special_administrative_region" and rows["HKG"]["parent_jurisdiction_id"] == "CHN"
    assert rows["JEY"]["kind"] == "crown_dependency" and rows["JEY"]["parent_jurisdiction_id"] is None
    assert rows["CYM"]["kind"] == "overseas_territory" and rows["CYM"]["parent_jurisdiction_id"] == "GBR"
    assert rows["SUP_EU"]["kind"] == "supranational" and rows["SUP_EU"]["iso3"] is None
    # Unclassified codes are left empty, not guessed.
    assert rows["FRA"]["kind"] is None


def test_registry_source_recorded(store):
    jurisdictions.seed(store)
    src = {r["source_id"]: r for r in store.rows("sources")}[jurisdictions.REGISTRY_SOURCE_ID]
    assert "LGPL-2.1" in src["licence_terms"]
