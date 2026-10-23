import pytest
from conftest import entity

from rscore.validation import ValidationError


@pytest.fixture
def law(seeded):
    seeded.insert("instruments", [{
        "instrument_id": "chn_hkg_dta_2006", "instrument_type": "bilateral_treaty",
        "title": "Arrangement between the Mainland of China and the Hong Kong SAR (test record)",
        "source_id": "test_src"}])
    seeded.insert("provisions", [{
        "provision_id": "chn_hkg_dta_2006_a10_2", "instrument_id": "chn_hkg_dta_2006", "pinpoint": "art 10(2)",
        "source_id": "test_src"}])
    return seeded


def regime(**kw):
    row = {"jurisdiction_id": "CHN", "variable": "cit_rate", "valid_from": "2008-01-01", "value": "0.25",
           "value_type": "rate", "rule_status": "source_backed", "verified": False, "source_id": "test_src"}
    row.update(kw)
    return row


def test_regime_value_with_provision_has_no_warning(law):
    report = law.insert("regime_values", [regime(provision_id="chn_hkg_dta_2006_a10_2", verified=True)])
    assert report.ok and not report.warnings


def test_regime_value_without_provision_warns(law):
    report = law.insert("regime_values", [regime()])
    messages = " ".join(str(w) for w in report.warnings)
    assert report.ok and "names no provision_id" in messages and "not yet verified" in messages


@pytest.mark.parametrize("row,message", [
    (regime(value="1.0"), "capped"),
    (regime(value_type="fraction", value="1.5"), r"\[0, 1\]"),
    (regime(value_type="number", value="abc"), "does not fit"),
    (regime(value_type="date", value="2025"), "does not fit"),
    (regime(rule_status="derived", verified=True), "must be source_backed"),
    (regime(provision_id="missing"), "not in provisions"),
])
def test_regime_value_errors(law, row, message):
    with pytest.raises(ValidationError, match=message):
        law.insert("regime_values", [row])


def test_proposition_links(law):
    law.insert("regime_values", [regime()])
    law.insert("propositions", [{"proposition_id": "p1", "text": "China's standard CIT rate is 25%.",
                                  "status": "draft"}])
    law.insert("proposition_links", [
        {"proposition_id": "p1", "target_table": "regime_values", "target_id": "CHN|cit_rate|2008-01-01",
         "role": "supports"},
        {"proposition_id": "p1", "target_table": "provisions", "target_id": "chn_hkg_dta_2006_a10_2",
         "role": "qualifies"},
    ])
    with pytest.raises(ValidationError, match="jurisdiction_id\\|variable\\|valid_from"):
        law.insert("proposition_links", [{"proposition_id": "p1", "target_table": "regime_values",
                                          "target_id": "CHN|cit_rate", "role": "supports"}])


def test_flow_parties_must_exist(seeded):
    seeded.insert("entities", [entity("a")])
    base = {"flow_id": "f1", "from_kind": "entity", "from_id": "a", "to_kind": "jurisdiction", "to_id": "HKG",
            "flow_type": "dividend", "amount": 10.0, "currency": "CNY", "period": "2025", "source_id": "test_src"}
    seeded.insert("flows", [base])
    with pytest.raises(ValidationError, match="from_id 'b' is not in entities"):
        seeded.insert("flows", [{**base, "flow_id": "f2", "from_id": "b"}])
