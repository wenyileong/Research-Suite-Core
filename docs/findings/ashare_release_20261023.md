# Findings from importing release `ashare_release_20261023T155523Z`

**Date:** 24 October 2026. **Release:** built with A-share Company Intelligence v2.0.6, database fingerprint `e56526f6…`. **Importer:** research-suite-core 0.3.0.

These are faults in the scraper's output, found by the importer's checks. They are recorded here for the scraper's next version; this repository does not change the scraper. No personal names appear in this note.

## Coverage

The release holds no subsidiary, control, entity or control-chain rows, and 16 shareholder rows (one company, 000563). The scraper's own quality report lists the same gaps. The Phase 3 gate (a real group in the Lab) cannot be met until those layers are collected.

## 1. Shareholder tables: columns shifted

In all 16 shareholder rows the columns are shifted: the shareholder type is printed onto the end of `shareholder_name` (for example `…有限责任公司国有法人`), the percentage stake sits in `change_shares`, and `ownership_pct` holds unrelated numbers (0.0, 46.0, −519.0). One name also carries another field's pseudonym after a separator. The importer rejects all 16 rows.

## 2. Pseudonymisation missed a natural person

Because the type is glued onto the name, the release's natural-person test (a name of two to five Chinese characters, or a stated person type) did not recognise one natural-person shareholder, whose real name appears in a release marked as pseudonymised. The release should not be shared until the parser is fixed and the release regenerated. A sturdier test would also treat 自然人 inside the name as a person type.

## 3. Revenue: candidates that disagree

Eleven company-years hold revenue candidates that disagree by more than 1 per cent. Three patterns appear:

- **Scale:** a factor of 1,000 (for example 000063: 133,895,460 against 133,895,500,000, a statement table read as yuan although printed in thousands) or of 100 (000158, 000333). The statement-table parser carries the higher confidence (0.7 against 0.65), so choosing by confidence would keep the wrong value.
- **A dropped leading digit:** 000078 (6,667,709,464 against 26,667,709,464) and 000301 (25,587,320,327 against 125,587,320,327).

- **No simple factor:** 000016, 000042, 000043, 000045 and 000060, which suggests a figure taken from the parent company's own statement or from another line.

Six further candidates are below 1 million yuan (for example 5.37 and 57.1), which cannot be a listed group's annual revenue.

Because the second pattern produces plausible-looking figures, revenue resting on a single candidate cannot be trusted until reviewed.

## 4. Consolidation scope not stated

All 186 revenue candidates in this release came from PDF parsers, which leave `consolidation_scope` empty. With `--assume-consolidated`, 62 company-years import after the checks above.

## Suggested fixes in the scraper

1. Shareholder table layout: detect the type column before the stake columns, and test against tables where the type is printed in the name column.
2. Pseudonymisation: treat a name containing 自然人, or any row from a misaligned table, as possibly a person.
3. Statement tables: read the unit line (单位：元 / 千元 / 万元) before scaling, and cross-check revenue against the text summary where both exist.
4. Record `consolidation_scope` for PDF statement tables (合并 against 母公司).
