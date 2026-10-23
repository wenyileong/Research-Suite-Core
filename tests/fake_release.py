"""Build a small A-share release folder with the real release's column headers (v2.0.6)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

HEADERS = {
    "companies": "id,security_code,exchange,board,legal_name_cn,short_name_cn,legal_name_en,status,listing_date,org_id,source_last_seen,created_at,updated_at",
    "ownership_observations": "id,company_id,disclosure_id,observation_date,shareholder_name,shareholder_type,relationship,shares,ownership_pct,tradable_shares,pledged_shares,restricted_shares,change_shares,change_pct,is_controlling_shareholder,is_actual_controller,rank,source_document,source_page,extraction_method,confidence,source,raw_text,validation_status,entity_id,shareholder_nature,extraction_note,retrieved_at",
    "subsidiary_observations": "id,company_id,disclosure_id,observation_date,entity_name,relationship,principal_place,registered_place,jurisdiction_class,business_nature,direct_pct,indirect_pct,total_pct,acquisition_method,consolidated,registered_capital,total_assets,net_assets,revenue,net_profit,source,source_document,source_page,raw_value,extraction_method,confidence,validation_status,entity_id,extraction_note,retrieved_at",
    "control_observations": "id,company_id,disclosure_id,observation_date,controlling_shareholder,controlling_nature,actual_controller,controller_nature,no_controlling_shareholder,no_actual_controller,ownership_type,ownership_basis,source,source_page,raw_value,extraction_method,confidence,retrieved_at",
    "control_edges": "id,company_id,observation_date,parent_name,child_name,parent_entity_id,child_entity_id,pct,basis,source,retrieved_at",
    "financial_facts": "id,company_id,disclosure_id,reporting_period,period_type,statement_type,metric,metric_cn,value,raw_value,unit,currency,consolidation_scope,source_document,source_page,source_xbrl_tag,source_label,source_context,extraction_method,confidence,validation_status,extraction_note,retrieved_at,created_at,updated_at",
}
DOC = "https://static.cninfo.com.cn/finalpage/2026-03-01/example.PDF"
#: A personal name used only to prove it never leaves the importer.
PERSON = "张三"


def _sh(i, company, name, kind, pct, date="2025-12-31", **kw):
    row = {"id": i, "company_id": company, "disclosure_id": 9, "observation_date": date, "shareholder_name": name,
           "shareholder_type": kind, "ownership_pct": pct, "rank": i, "source_document": DOC, "source_page": 80,
           "extraction_method": "PDF_TABLE_LAYOUT", "confidence": 0.8, "source": "CNINFO",
           "validation_status": "UNVALIDATED", "retrieved_at": "2026-10-19 09:51:30"}
    row.update(kw)
    return row


def _sub(i, name, place, direct, indirect="", total="", relationship="subsidiary"):
    return {"id": i, "company_id": 1, "disclosure_id": 9, "observation_date": "2025-12-31", "entity_name": name,
            "relationship": relationship, "registered_place": place, "direct_pct": direct, "indirect_pct": indirect,
            "total_pct": total, "source": "CNINFO", "source_document": DOC, "source_page": 120,
            "extraction_method": "PDF_TABLE_LAYOUT", "confidence": 0.8, "validation_status": "UNVALIDATED",
            "retrieved_at": "2026-10-19 09:51:30"}


TABLES = {
    "companies": [
        {"id": 1, "security_code": "000999", "exchange": "SZSE", "board": "SZSE_MAIN", "short_name_cn": "示例股份",
         "legal_name_cn": "示例股份有限公司", "listing_date": "2001-05-08"},
        {"id": 2, "security_code": "600998", "exchange": "SSE", "board": "SSE_MAIN", "short_name_cn": "错位股份"},
    ],
    "ownership_observations": [
        _sh(1, 1, "示例控股集团有限公司", "国有法人", 51.2),
        _sh(2, 1, "香港中央结算有限公司", "境外法人", 12.0),
        _sh(3, 1, PERSON, "境内自然人", 5.0),
        _sh(4, 1, "某某投资有限公司国有法人", "", 0.0, date="2024-12-31", change_shares=4.1),  # shifted table
        _sh(5, 2, "甲投资有限公司", "境内非国有法人", 70.0),
        _sh(6, 2, "乙投资有限公司", "境内非国有法人", 40.0),                # with row 5: over 100
        _sh(7, 2, "丙投资有限公司", "境内非国有法人", -519.0),
    ],
    "subsidiary_observations": [
        _sub(1, "示例（香港）有限公司", "香港", 100),
        _sub(2, "示例开曼控股有限公司", "开曼群岛", 100),
        _sub(3, "示例科技（深圳）有限公司", "广东省深圳市", 70, 0),
        _sub(4, "示例合营有限公司", "上海", 0, 49, 49, relationship="joint_venture"),
        _sub(5, "示例欧洲有限公司", "欧洲", 100),
        _sub(6, "示例维京有限公司", "维尔京群岛", 100),
    ],
    "control_observations": [
        {"id": 1, "company_id": 1, "disclosure_id": 9, "observation_date": "2025-12-31",
         "controlling_shareholder": "示例控股集团有限公司", "controlling_nature": "国有法人",
         "actual_controller": "某省人民政府国有资产监督管理委员会", "controller_nature": "地方国资委",
         "source": "CNINFO", "source_page": 85, "extraction_method": "PDF_TEXT", "confidence": 0.7},
    ],
    "control_edges": [],
    "financial_facts": [
        {"id": 1, "company_id": 1, "disclosure_id": 9, "reporting_period": "2025-12-31", "period_type": "FY",
         "metric": "revenue", "value": 1.5e10, "unit": "CNY_1M", "currency": "CNY",
         "consolidation_scope": "CONSOLIDATED_DEFAULT", "source_document": DOC, "source_page": 17,
         "extraction_method": "XBRL", "confidence": 0.98},
        {"id": 2, "company_id": 2, "disclosure_id": 10, "reporting_period": "2025-12-31", "period_type": "FY",
         "metric": "revenue", "value": 3.0e9, "unit": "CNY_1M", "currency": "CNY", "consolidation_scope": "",
         "source_document": DOC, "source_page": 12, "extraction_method": "PDF_TEXT_HEURISTIC", "confidence": 0.65},
        # A statement table read as yuan although printed in thousands: 1,000 times too small.
        {"id": 3, "company_id": 2, "disclosure_id": 10, "reporting_period": "2025-12-31", "period_type": "FY",
         "metric": "revenue", "value": 3.0e6, "unit": "CNY", "currency": "CNY", "consolidation_scope": "",
         "source_document": DOC, "source_page": 95, "extraction_method": "PDF_STATEMENT_TABLE", "confidence": 0.7},
        {"id": 4, "company_id": 2, "disclosure_id": 10, "reporting_period": "2025-12-31", "period_type": "FY",
         "metric": "revenue", "value": 57.1, "unit": "CNY", "currency": "CNY", "consolidation_scope": "",
         "source_document": DOC, "source_page": 3, "extraction_method": "PDF_TEXT_HEURISTIC", "confidence": 0.65},
    ],
}


def build(folder: Path, pseudonymised: bool = True) -> Path:
    (folder / "csv").mkdir(parents=True, exist_ok=True)
    for table, header in HEADERS.items():
        cols = header.split(",")
        with (folder / "csv" / f"{table}.csv").open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="raise")
            w.writeheader()
            for row in TABLES[table]:
                w.writerow({c: row.get(c, "") for c in cols})
    manifest = {
        "name": "ashare_release_test", "created_utc": "2026-10-23T15:56:51",
        "software": {"name": "A-share Company Intelligence", "version": "2.0.6"},
        "database_fingerprint": "abcdef0123456789" * 4,
        "row_counts": {"companies": 2},
        "pseudonymisation": {"applied": pseudonymised},
        "citation": "A-share Company Intelligence dataset release 'ashare_release_test' (2026).",
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return folder
