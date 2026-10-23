# Licence audit of the three research tools

**Date:** 23 October 2026. **Phase:** 1 (governance and licence audit). **Status:** complete for the revisions listed below.

**Result:** none of the three distributed Windows builds bundles copyleft code outside a recognised exception. Two follow-ups remain: the Lab's build should ship full third-party licence texts, and two optional components must stay out of any future build.

## Revisions audited

| Repository | Revision | Licence of the project's own code |
| --- | --- | --- |
| `wenyileong/ashare-company-intelligence` | `46a892d` (23 October 2026) | PolyForm Strict 1.0.0 |
| `wenyileong/international-tax-network-lab` | `9623dd6` (22 October 2026) | None granted yet ("all rights reserved"; decision open) |
| `wenyileong/jaf-rule-bench` | `5ac62b1` (19 October 2026) | PolyForm Noncommercial 1.0.0 (code); CC BY-NC 4.0 (documents, templates, data) |

## Method

1. Read each repository's dependency manifests (`requirements*.txt`, `pyproject.toml`, `requirements/build.in`) and its PyInstaller specification (to see what the Windows build includes and excludes).
2. Installed each repository's dependencies, including optional and test extras, into a separate virtual environment (Python 3.13, latest versions allowed by the manifests).
3. Read the licence metadata of every installed distribution (`License-Expression`, `License` and classifiers) and, where the metadata was unclear, the licence file shipped in the distribution.
4. Read the header of every vendored file (`web/vendor/plotly.min.js`).
5. Read each repository's notices handling (`THIRD_PARTY_NOTICES.txt`, `packaging/third_party_notices.py`, `LICENSE`).

The versions installed are the latest the manifests allow, which may differ from the versions in a given release build. Licence terms rarely change between minor versions, but each release build should regenerate its notices from the environment it was built in, as the scraper and the Rule Bench already do.

## A-share Company Intelligence

**Interface:** tkinter (Tcl/Tk, BSD-style licence). **Notices:** generated at build time by `packaging/third_party_notices.py`, including Tcl/Tk, PDFium and the MPL-2.0 position of certifi. No action needed.

| Component | Licence | In the Windows build | Note |
| --- | --- | --- | --- |
| httpx, httpcore, idna | BSD-3-Clause | Yes | |
| h11, anyio | MIT | Yes | |
| certifi | MPL-2.0 | Yes | File-level copyleft. Distributing it unmodified is permitted; the notices already point to its source. |
| SQLAlchemy, alembic, Mako | MIT | Yes | |
| MarkupSafe | BSD-3-Clause | Yes | |
| beautifulsoup4, soupsieve | MIT | Yes | |
| lxml | BSD-3-Clause | Yes | Bundles libxml2 and libxslt (MIT). |
| typer, rich, markdown-it-py, mdurl, annotated-doc | MIT | Yes | |
| shellingham | ISC | Yes | |
| Pygments | BSD-2-Clause | Yes | |
| pypdf | BSD-3-Clause | Yes | |
| pypdfium2 | BSD-3-Clause or Apache-2.0, with PDFium's licences | Yes | |
| typing_extensions | PSF-2.0 | Yes | |
| CPython, Tcl/Tk | PSF-2.0; Tcl/Tk licence | Yes | |
| PyInstaller bootloader | GPL-2.0-or-later with the Bootloader Exception | Yes | The exception permits distributing the bundled program on any terms. |
| matplotlib, numpy, Pillow, reportlab, pytest | Matplotlib licence, BSD-3-Clause, MIT-CMU, BSD, MIT | No (excluded in `ashare.spec`) | Optional or development only. |
| pyarrow | Apache-2.0 | No | Optional source install. |
| duckdb | MIT | No | Optional source install. |
| **psycopg, psycopg-binary** | **LGPL-3.0-only** | **No** | **Optional PostgreSQL back end. Must stay out of any Windows build.** |

## International Tax Network Lab

**Interface:** a local web page served by the program, with Plotly.js vendored. **Notices:** `LICENSE` names Plotly.js and NetworkX but does not reproduce their licence texts.

| Component | Licence | In the Windows build | Note |
| --- | --- | --- | --- |
| NetworkX | BSD-3-Clause | Yes | Licence text must accompany binary distributions. |
| Plotly.js 4.1.1 (vendored) | MIT | Yes | Licence text must accompany copies. |
| CPython | PSF-2.0 | Yes | Not yet listed. |
| PyInstaller bootloader | GPL-2.0-or-later with the Bootloader Exception | Yes | Not yet listed. |
| pytest | MIT | No (test) | |
| hypothesis | MPL-2.0 | No (test; excluded in `taxnetlab.spec`) | |
| ripser, persim | MIT | No (optional differential checks) | |
| **gudhi** | **MIT for GUDHI's own code (the wheel's licence file); some modules are built on CGAL, most of whose packages are GPL-3.0-or-later. Whether this wheel compiles in GPL code was not verified.** | **No (optional differential checks)** | **Keep out of any build; use only as a private test oracle.** |
| numpy, scipy, pandas, scikit-learn | BSD-3-Clause | No (optional or excluded) | |

**Action for the Lab (when its licence is decided):** add a `THIRD_PARTY_NOTICES.txt` reproducing the full licence texts of NetworkX, Plotly.js, CPython and the PyInstaller bootloader, generated at build time as in the other two repositories. This repository does not change the Lab; the action is recorded here for the Lab's next release.

## JAF Rule Bench

**Interface:** a local web page served by the program. **Notices:** `THIRD_PARTY_NOTICES.txt`, generated by `tools/make_third_party_notices.py`, covering CPython, NumPy (with OpenBLAS, LAPACK and the GCC runtime under its exception), openpyxl, et_xmlfile, the PyInstaller bootloader and the Microsoft Visual C++ runtime. No action needed.

## Consequences for the roadmap

1. **Interface framework (roadmap decision 1):** settled. No tool uses Qt; the interfaces are tkinter and local web pages, so the PySide6 and PyQt question does not arise.
2. **Storage engine:** the roadmap proposed DuckDB for the shared store. The Lab deliberately keeps its core free of numerical libraries to keep the executable small. The shared core therefore uses the standard library's `sqlite3`, with DuckDB as an optional export, matching the scraper's existing optional `export-duckdb`.
3. **Gate for Phase 1:** passed, subject to the Lab notices action above.
