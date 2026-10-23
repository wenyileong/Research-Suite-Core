# Shared data model, version 1

**Date:** 23 October 2026. **Phase:** 2 (shared core). **Schema generation:** 1. **Implemented in:** `src/rscore/schema.py`.

The shared model adopts the International Tax Network Lab's conventions unchanged and extends them, so that a snapshot of the shared store can be exported as a dataset the Lab already reads.

## 1. Conventions

These follow the Lab's project plan (v2.1, s 5.1) and its `schema.py`.

| Kind of value | Rule |
| --- | --- |
| Shares, rates, percentages | Fractions in [0, 1] (35% is `0.35`). Tax rates are capped at 0.9999. |
| Money | An amount plus an ISO 4217 currency code. `XTS` (the ISO code reserved for testing) marks synthetic data. |
| Real jurisdictions | ISO 3166-1 alpha-3 codes (`CHN`, `HKG`, `CYM`). |
| Fictional jurisdictions | The reserved `FIC_` prefix (`FIC_A`). |
| Groupings that are not ISO territories | The reserved `SUP_` prefix (`SUP_EU`). New in the shared model. |
| Dates | ISO 8601 calendar dates (`YYYY-MM-DD`). |
| Periods | A year (`2025`), a quarter (`2025Q1`) or a date range (`2025-01-01/2025-06-30`). |
| Identifiers | 1 to 64 characters from letters, digits, `_ . : -`. |
| Validity in time | Records that can change carry `valid_from` and `valid_to`; an empty `valid_to` means still in force. |
| Provenance | Every factual row names a `source_id` in `sources`. |
| Natural persons | Excluded or pseudonymised before they enter the store. |

## 2. Tables

Tables marked **Lab** have the same name and the same columns as the Lab's tables, plus any columns listed as extensions. Export to the Lab drops the extensions.

### Sources and jurisdictions

| Table | Origin | Primary key | Purpose |
| --- | --- | --- | --- |
| `sources` | Lab, extended | `source_id` | Where every record came from and on what terms. Extensions: `content_sha256` (hash of the file or response retrieved), `extraction_method`. |
| `jurisdictions` | Lab, extended | `jurisdiction_id` | Taxing territories. Extensions: `kind`, `valid_from`, `valid_to`, `note`. |
| `jurisdiction_aliases` | New | `alias`, `language` | Names in other languages or forms (`开曼群岛`, `BVI`) mapped to a jurisdiction, for importers such as the scraper converter. |
| `jurisdiction_attributes` | Lab | `jurisdiction_id`, `attribute`, `period` | Contextual time series such as GDP, with unit and source. |

`kind` takes one of: `sovereign_state`, `special_administrative_region`, `crown_dependency`, `overseas_territory`, `other_territory`, `supranational`, `fictional`. It is left empty where a code has not been classified, rather than guessed. Version 1 classifies Hong Kong and Macau (special administrative regions, parent `CHN`), Guernsey, Jersey and the Isle of Man (Crown Dependencies, no parent), the twelve British Overseas Territories with their own ISO codes (parent `GBR`) and the European Union (`SUP_EU`). `parent_jurisdiction_id` records sovereignty only; it does not imply a shared tax system.

### Firms and ownership

| Table | Origin | Primary key | Purpose |
| --- | --- | --- | --- |
| `entities` | Lab | `entity_id` | Legal entities with jurisdiction, type and validity. |
| `ownership` | Lab | `relation_id` | Direct relations stored holder to held: `equity`, `voting`, `control` or `economic_interest`. Indirect holdings are derived, never stored. |
| `entity_financials` | Lab | `entity_id`, `period` | Operating revenue by entity and period, with consolidation status. |
| `flows` | New | `flow_id` | Payments and investment between entities or jurisdictions: dividends, interest, royalties, service fees, FDI positions and flows. |

### Law

| Table | Origin | Primary key | Purpose |
| --- | --- | --- | --- |
| `instruments` | New | `instrument_id` | Treaties, the Multilateral Instrument, statutes, regulations and guidance, with signature, entry into force and termination dates. |
| `instrument_parties` | New | `instrument_id`, `jurisdiction_id` | Parties to an instrument, with ratification date and whether a treaty is a covered tax agreement under the MLI. |
| `provisions` | New | `provision_id` | A pinpointed rule (`art 10(2)(a)`) in an instrument, with validity dates and a hash of its text. |
| `regime_values` | New | `jurisdiction_id`, `variable`, `valid_from` | Coded rules in long form: one variable per row (for example `cit_rate`, or a Rule Bench liability setting), with its type, unit, validity, status, verification flag and the provision it rests on. |
| `authorities` | New | `authority_id` | Cases, rulings and official guidance, with OSCOLA citation, court or body, jurisdiction and date. |
| `propositions` | New | `proposition_id` | A legal claim the software relies on, with its status (`draft`, `verified`, `disputed`, `superseded`) and who verified it, when. |
| `proposition_links` | New | `proposition_id`, `target_table`, `target_id` | Links a proposition to the provisions, authorities or regime values that support, qualify or contradict it, with a pinpoint. |

`rule_status` follows the Lab: `source_backed`, `derived` or `synthetic_assumption`.

### Bookkeeping (not part of a snapshot's content)

| Table | Purpose |
| --- | --- |
| `meta` | Schema generation and creation time of the store. |
| `snapshots` | Each snapshot taken: identifier, UTC time, schema generation, per-table hashes, row counts and a note. |

## 3. Integrity rules

The rules mirror the Lab's own validation (`taxnetlab/datasets.py`), so that the shared store never accepts data the Lab would reject, and never rejects data the Lab accepts. Errors block a write; warnings are reported and the write goes ahead.

**Errors**

1. Every `source_id`, `jurisdiction_id`, `entity_id`, `instrument_id`, `provision_id` and `proposition_id` that a row names must exist in its table. `flows` parties and `proposition_links` targets are checked against the table their kind names.
2. `valid_to`, where given, is not earlier than `valid_from`.
3. `entities.is_natural_person` must be false: natural persons are excluded before import.
4. Synthetic data stays on fictional jurisdictions: an entity whose source is `synthetic`, or a `regime_values` row whose `rule_status` is `synthetic_assumption`, may not sit on a real jurisdiction.
5. `ownership.direct` must be true: indirect holdings are derived, never stored. A `value_amount` needs a `value_currency`.
6. `fictional` is true exactly when the identifier starts with `FIC_`; `iso3`, where given, equals the identifier of a real jurisdiction; a `SUP_` identifier has kind `supranational`; no jurisdiction is its own parent.
7. Fractions lie in [0, 1]. In `regime_values`, `value_type` `fraction` and `rate` lie in [0, 1], and a `rate` is capped at 0.9999.
8. A `regime_values` row marked `verified` must be `source_backed`.

**Warnings**

1. An entity holds itself (possible treasury shares).
2. An ownership row reports no `fraction` (it is never imputed).
3. A `source_backed` `regime_values` row names no `provision_id`, or a non-synthetic row is not yet verified.
4. From `Store.validate()` only, which looks at the whole store: current equity fractions in one entity sum above 1 (tolerance 1e-6), and ownership cycles (cross-holdings).

## 4. Snapshots and hashing

A snapshot freezes the store's content so that a figure can be regenerated. It uses the Lab's canonical form (`canonical.py`): each table as CSV, rows sorted by primary key, columns in schema order, floats in Python's shortest round-trip form, booleans `true`/`false`, empty values as empty strings, UTF-8, lines ending in `\n`. The table hash is the SHA-256 of that text; the snapshot identifier is the SHA-256 of the sorted list of `table:hash` lines. Empty tables do not enter the identifier, so adding a table in a later generation never changes existing snapshot identifiers.

Hashes detect change. They do not establish that data are authentic or correct.

## 5. Export to the Lab

`rscore.export.lab_dataset()` writes the Lab tables (`sources`, `jurisdictions`, `jurisdiction_attributes`, `entities`, `ownership`, `entity_financials`) as CSV files with exactly the Lab's columns, ready for the Lab's import. Rows whose `licence_class` is `licensed_no_redistribution` are kept, because the Lab enforces redistribution limits itself at export time.

## 6. Not in version 1

- Mapping `regime_values` to the Lab's tax tables (`tax_domestic`, `tax_treaty_dividends`, `tax_relief_overrides`, `tax_treaty_conditions`). This needs the treaty module (Phase 6) and is planned with the counterfactuals work (Phase 5).
- Reading the scraper's release database (Phase 3).
- Literature records (Phase 7).
