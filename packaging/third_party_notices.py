"""Write THIRD_PARTY_NOTICES.txt for the launcher, from the licence files of the Python that built it.

ResearchSuite.exe bundles three third-party components: CPython (with its standard library), Tcl/Tk
(for the window) and the PyInstaller bootloader. This script copies their licence texts from the build
environment, so the notices always match what was bundled. Run it with the same Python that ran
PyInstaller:

    python packaging/third_party_notices.py dist/THIRD_PARTY_NOTICES.txt
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
#: Official Tcl and Tk licence texts, used when the build environment does not ship license.terms
#: (Python's Windows installs place the Tcl library in tcl/, but not always the licence file).
FALLBACK = {"tcl": HERE / "licences" / "tcl-license.terms", "tk": HERE / "licences" / "tk-license.terms"}
SOURCES: dict[str, str] = {}


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _first(*paths: Path, label: str = "") -> str | None:
    for p in paths:
        text = _read(p)
        if text:
            if label:
                SOURCES[label] = str(p)
            return text
    return None


def _tcl_tk(kind: str, base: Path) -> str | None:
    """licence.terms for Tcl or Tk: from Python's own tcl folder, a system Tcl, or the bundled copy."""
    found = sorted(p for p in (base / "tcl").rglob("license.terms") if p.parent.name.lower().startswith(kind)) \
        if (base / "tcl").is_dir() else []
    system = sorted(Path("/usr/share/tcltk").glob(f"{kind}8*/license.terms"))
    return _first(*found, *system, FALLBACK[kind], label=kind)


def sections() -> list[tuple[str, str, str | None]]:
    base = Path(sys.base_prefix)
    out = []
    out.append((
        f"CPython {platform.python_version()} (interpreter and standard library)",
        "Python Software Foundation License Version 2, with the licences of its bundled parts",
        _first(base / "LICENSE.txt", base / "LICENSE", Path(sys.prefix) / "LICENSE.txt",
               base / "lib" / f"python{sys.version_info[0]}.{sys.version_info[1]}" / "LICENSE.txt", label="cpython"),
    ))
    import tkinter

    out.append((f"Tcl {tkinter.TclVersion}", "Tcl/Tk licence (BSD-style)", _tcl_tk("tcl", base)))
    out.append((f"Tk {tkinter.TkVersion}", "Tcl/Tk licence (BSD-style)", _tcl_tk("tk", base)))
    try:
        import PyInstaller

        pkg = Path(PyInstaller.__file__).resolve().parent
        boot = _first(pkg.parent / f"pyinstaller-{PyInstaller.__version__}.dist-info" / "licenses" / "COPYING.txt",
                      pkg.parent / f"pyinstaller-{PyInstaller.__version__}.dist-info" / "COPYING.txt",
                      pkg / "COPYING.txt", label="pyinstaller")
        version = PyInstaller.__version__
    except ImportError:
        boot, version = None, "unknown"
    out.append((
        f"PyInstaller bootloader {version}",
        "GNU General Public License version 2 or later, with the Bootloader Exception, which permits "
        "distribution of the bundled program under any terms",
        boot,
    ))
    return out


def render() -> str:
    parts = sections()
    lines = [
        "Research Suite launcher: third-party notices",
        "=" * 44,
        "",
        "ResearchSuite.exe bundles the third-party components listed below. Each remains under its own",
        "licence, reproduced in full in this file. The launcher's own code is not covered by these",
        "licences (see LICENSE).",
        "",
    ]
    lines += [f"  - {name}: {licence}" for name, licence, _ in parts]
    for name, licence, body in parts:
        lines += ["", "", "=" * 78, name, f"Licence: {licence}", "=" * 78, ""]
        lines.append(body if body else "(Licence text not found in the build environment; see the project's website.)")
    return "\n".join(lines) + "\n"


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("THIRD_PARTY_NOTICES.txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    text = render()
    target.write_text(text, encoding="utf-8")
    missing = text.count("(Licence text not found")
    print(f"wrote {target} ({missing} licence text(s) missing)")
    for label, source in sorted(SOURCES.items()):
        print(f"  {label}: {source}")
    if os.environ.get("GITHUB_ACTIONS"):
        # Annotations are visible in the run summary and through the API.
        used = "; ".join(f"{k}={Path(v).name if 'licences' in v else v}" for k, v in sorted(SOURCES.items()))
        print(f"::notice title=Third-party notices::{missing} missing; sources: {used}")
        if missing:
            print(f"::error title=Third-party notices::{missing} licence text(s) not found")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
