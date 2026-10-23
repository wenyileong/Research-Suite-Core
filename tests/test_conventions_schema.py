import datetime as dt

import pytest

from rscore import conventions as cv
from rscore import schema as sc


@pytest.mark.parametrize("period,start,end", [
    ("2025", dt.date(2025, 1, 1), dt.date(2025, 12, 31)),
    ("2025Q1", dt.date(2025, 1, 1), dt.date(2025, 3, 31)),
    ("2024Q4", dt.date(2024, 10, 1), dt.date(2024, 12, 31)),
    ("2025-02-01/2025-02-28", dt.date(2025, 2, 1), dt.date(2025, 2, 28)),
])
def test_periods(period, start, end):
    assert cv.parse_period(period) == (start, end)


@pytest.mark.parametrize("bad", ["25", "2025Q5", "2025-03-01/2025-02-01", "FY2025", "2025-1-1/2025-12-31"])
def test_bad_periods(bad):
    with pytest.raises(ValueError):
        cv.parse_period(bad)


@pytest.mark.parametrize("jid,ok", [
    ("CHN", True), ("FIC_A", True), ("SUP_EU", True), ("chn", False), ("CN", False), ("FIC_", False), ("EU", False),
])
def test_jurisdiction_ids(jid, ok):
    assert cv.is_jurisdiction_id(jid) is ok


def test_coerce_types():
    assert sc.coerce(sc.Column("x", sc.BOOL), "Yes") is True
    assert sc.coerce(sc.Column("x", sc.FLOAT, minimum=0, maximum=1), "0.35") == 0.35
    assert sc.coerce(sc.Column("x"), "  ") is None
    with pytest.raises(ValueError, match="above the maximum"):
        sc.coerce(sc.Column("x", sc.FLOAT, maximum=1), 1.5)
    with pytest.raises(ValueError, match="finite"):
        sc.coerce(sc.Column("x", sc.FLOAT), "inf")
    with pytest.raises(ValueError, match="ISO 4217"):
        sc.coerce(sc.Column("x", sc.CURRENCY), "rmb")
    with pytest.raises(ValueError, match="not one of"):
        sc.coerce(sc.Column("x", choices=("a", "b")), "c")
    with pytest.raises(ValueError):
        sc.coerce(sc.Column("x", sc.DATE), "23/10/2026")


def test_lab_columns_exist_in_shared_tables():
    for table, columns in sc.LAB_COLUMNS.items():
        assert set(columns) <= set(sc.SCHEMAS[table].column_names), table


def test_references_point_at_earlier_tables():
    seen = set()
    for name in sc.TABLE_ORDER:
        for col in sc.SCHEMAS[name].columns:
            if col.references:
                ref_table, ref_col = col.references.split(".")
                assert ref_table in seen | {name}, f"{name}.{col.name}"
                assert ref_col in sc.SCHEMAS[ref_table].column_names
        seen.add(name)
