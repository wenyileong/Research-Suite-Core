# Research Suite Core

<img src="packaging/icon/research_suite.svg" alt="Research Suite icon" width="72" align="right">

The shared core and launcher of a research software suite for international tax, corporate structure and legal research. The core holds what the suite's tools share: one data model, one jurisdiction registry, provenance for every value, and snapshots that let any figure be regenerated. The launcher, `ResearchSuite.exe`, opens the tools from one window.

The suite brings together three existing tools, which this repository reads from but does not change:

| Tool | Repository | Role |
| --- | --- | --- |
| A-share Company Intelligence | `wenyileong/ashare-company-intelligence` | Firm-level data on Chinese listed groups, with provenance |
| International Tax Network Lab | `wenyileong/international-tax-network-lab` | Tax routing, conduits and sinks, topological data analysis |
| JAF Rule Bench | `wenyileong/jaf-rule-bench` | Coding and testing of jurisdictional assignment regimes |

The core adopts the Lab's data conventions unchanged (fractions, ISO 3166-1 alpha-3 codes, ISO 4217 currencies, the `FIC_` prefix, licence classes and canonical hashing), so a snapshot of the shared store exports as a dataset the Lab already imports.

## Status

Version 0.2.0 covers Phase 1 and most of Phase 2 of the development roadmap.

| Phase | Status |
| --- | --- |
| 1. Governance and licence audit | Done: [`docs/licence_audit_2026-10-23.md`](docs/licence_audit_2026-10-23.md), clean-room process, inspiration register |
| 2. Shared core | In progress: data model v1, store, jurisdiction registry, snapshots, Lab export and the launcher done; the tools do not yet read or write the shared store |
| 3 onwards | Not started |

## What is here

| Path | Contents |
| --- | --- |
| `src/rscore/conventions.py` | Value conventions and closed vocabularies |
| `src/rscore/schema.py` | The 15 content tables of data model v1, and the Lab's exact columns |
| `src/rscore/store.py` | The SQLite store: migrations, validated writes, whole-store checks |
| `src/rscore/jurisdictions.py` | The jurisdiction registry (250 records) |
| `src/rscore/snapshot.py` | Canonical hashing, snapshot export and verification |
| `src/rscore/export.py` | Export to the Lab's dataset format |
| `src/rscore/launcher/` | The launcher: tool detection, saved settings, English and Chinese text, the window |
| `packaging/` | The PyInstaller specification, icon, notices script and quick-start note for `ResearchSuite.exe` |
| `docs/data_model_v1.md` | The data model specification |
| `docs/cleanroom/` | The clean-room process and its specification template |
| `docs/inspiration_register.csv` | Every open-source reference, its licence and how it is used |

## The launcher

`ResearchSuite.exe` shows the three tools with an Open and a Locate button each. It finds a tool where its installer puts it, or in a folder beside or inside the launcher's own folder; for anything else, Locate saves the tool's location. The window switches between English and Simplified Chinese, and remembers the choice. The launcher does not contain the tools: each stays a separate program with its own licence.

The icon (`packaging/icon/research_suite.svg`) shows three nodes for the suite's three levels of analysis, joined to a hub for the shared core: red for firms (A-share Company Intelligence), green for networks (the Lab) and amber for regimes (JAF Rule Bench), on the Lab's indigo. `packaging/icon/make_icon.py` redraws every size from that design (it needs Pillow, a development-only dependency).

**Getting the exe.** GitHub builds it on a Windows runner: in the repository's Actions tab, choose *build-windows*, then *Run workflow*, and download the `ResearchSuite-windows` zip from the finished run. Pushing a tag such as `v0.2.0` also starts a build. To build on your own Windows computer instead, run `build_windows.bat` (Python 3.11 or later from python.org); the result is in `release\`.

To run the launcher from source: `python -m rscore.launcher` (with `src` on the Python path).

## Using the core

The core needs Python 3.11 or later and nothing outside the standard library.

```python
from rscore import export, jurisdictions, snapshot
from rscore.store import Store

with Store("project.sqlite") as store:
    jurisdictions.seed(store)
    store.insert("sources", [{"source_id": "cninfo_2025", "title": "CNINFO annual reports 2025",
                              "licence_class": "public_attribution"}])
    store.insert("entities", [{"entity_id": "e1", "reported_name": "Example Holdings Ltd",
                               "jurisdiction_id": "CYM", "entity_type": "company",
                               "is_natural_person": False, "source_id": "cninfo_2025"}])
    print(store.validate())
    snapshot.export(store, "snapshots", note="example")
    export.lab_dataset(store, "lab_import")
```

A batch that fails validation raises `ValidationError` and writes nothing; its message lists every problem in plain English.

## Tests

```
pip install pytest
python -m pytest
```

One test checks the export against the Lab's own importer. It runs only when `TAXNETLAB_SRC` points to the `src` folder of a Lab checkout:

```
TAXNETLAB_SRC=../international-tax-network-lab/src python -m pytest
```

## Licence

No licence is granted yet; see [`LICENSE`](LICENSE). The ISO 3166 code list in `src/rscore/data/iso3166.json` comes from the Debian iso-codes data (LGPL-2.1), as distributed with the International Tax Network Lab.

## Acknowledgements

Developed with the assistance of Claude (Anthropic).
