# Importer: A-share Company Intelligence release

**Phase:** 3. **Module:** `src/rscore/importers/ashare.py`. **Command:** `python -m rscore import-ashare RELEASE_DIR`.

The importer reads a release folder (`manifest.json` and `csv/`), never the scraper's working database. It follows the International Tax Network Lab's import note (`docs/ASHARE_IMPORT_NOTE.md` in the Lab's repository). Misparsed rows are rejected with a reason, never repaired.

## Field mapping

| Release table | Shared table | Mapping |
| --- | --- | --- |
| `companies` | `entities` | `ashare:co:<security_code>`; legal name, else short name; jurisdiction `CHN`; type `listed_company`; listing date as `valid_from`. Created only for companies with an imported row. |
| `ownership_observations` | `entities`, `ownership` | Holder `ashare:org:<hash of name>` holds the listed company; `equity`; fraction `ownership_pct / 100`; `valid_from` the observation date. |
| `subsidiary_observations` | `entities`, `ownership` | The listed company holds the subsidiary; fraction `direct_pct / 100` (or `total_pct` when no indirect stake is reported); jurisdiction from `registered_place`, else `principal_place`. |
| `control_observations` | `entities`, `ownership` | The controlling shareholder holds a `control` relation over the listed company, with no fraction. Actual controllers are counted but not stored, because they control indirectly. |
| `control_edges` | `entities`, `ownership` | Each disclosed link in a control chain: `equity` with its fraction where stated, else `control`. |
| `financial_facts` (`revenue`, `FY`) | `entity_financials` | Annual revenue in yuan (the scraper has already scaled it); consolidated when the scope is `CONSOLIDATED_DEFAULT`. |
| manifest and each document page | `sources` | One source for the release (with its database fingerprint and citation) and one per disclosure document and page (URL, retrieval date, extraction method, confidence, validation status). |

Identifiers carry the first eight characters of the release's database fingerprint, so re-importing the same release replaces its rows rather than duplicating them.

## Rejection rules

| Reason | Rule |
| --- | --- |
| `natural_person_excluded` | A stated person type, a pseudonym (`P` and 12 hexadecimal digits), 自然人 in the name, or a name of two to five Chinese characters with no organisation word. Such names are never written to the store or any report; a name that was not pseudonymised is counted and reported as a privacy warning. |
| `table_columns_shifted` | Any row of a company's shareholder table for one date has a shareholder type glued onto the name, or another field's pseudonym inside the name. The whole table is rejected, because the shift misplaces every stake in it. |
| `stake_missing`, `stake_outside_0_100` | No stake, or a stake outside (0, 100] per cent. |
| `stakes_sum_over_100` | The stakes of one table sum above 100.5 per cent (0.5 points allowed for rounding). |
| `holder_jurisdiction_needs_review` | A holder whose type does not state a domestic holder (境内, 国有, 国家) and is not in the overrides. The name and a suggestion from `rscore.places` go to `review_jurisdictions.csv`. |
| `place_unmatched`, `place_ambiguous`, `place_missing` | A subsidiary's place that names no single jurisdiction (for example 欧洲, or 维尔京群岛 without 英属 or 美属). |
| `no_direct_stake`, `indirect_only` | No direct stake is reported. |
| `consolidation_scope_not_stated` | Revenue read from a PDF has no scope; pass `--assume-consolidated` to accept it as consolidated (the report records the assumption). |
| `revenue_implausibly_small` | Below 1 million yuan. |
| `revenue_candidates_disagree` | Candidates for one company and year differ by more than 1 per cent. All are rejected and listed in `review_revenue.csv`, because the disagreement usually reveals a scale or digit error that choosing by confidence would hide. |
| `below_min_confidence` | Below `--min-confidence`, or marked `REJECTED` in the scraper's review. |

## Review loop

1. Run the import. The report folder holds `import_report.md`, `import_report.json`, `rejected_rows.csv` (release table, row id, reason) and the two review files.
2. Fill in `jurisdiction_id` in `review_jurisdictions.csv` (the suggestion column helps) and run the import again with `--overrides review_jurisdictions.csv`. Overrides apply to holder names and to places.
3. Resolve revenue conflicts in A-share Company Intelligence's own review queue, then make a new release.

`--accept-suggestions` takes every name-based suggestion without review; the report records that it was used.
