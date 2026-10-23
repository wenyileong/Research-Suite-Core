"""Write THIRD_PARTY_NOTICES.txt for the launcher, from the licence files of the Python that built it.

ResearchSuite.exe bundles three third-party components: CPython (with its standard library), Tcl/Tk
(for the window) and the PyInstaller bootloader. This script copies their licence texts from the build
environment, so the notices always match what was bundled. Run it with the same Python that ran
PyInstaller:

    python packaging/third_party_notices.py dist/THIRD_PARTY_NOTICES.txt
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _first(*paths: Path) -> str | None:
    for p in paths:
        text = _read(p)
        if text:
            return text
    return None


def sections() -> list[tuple[str, str, str | None]]:
    base = Path(sys.base_prefix)
    out = []
    out.append((
        f"CPython {platform.python_version()} (interpreter and standard library)",
        "Python Software Foundation License Version 2, with the licences of its bundled parts",
        _first(base / "LICENSE.txt", base / "LICENSE",
               Path(sys.prefix) / "LICENSE.txt", base / "lib" / f"python{sys.version_info[0]}.{sys.version_info[1]}" / "LICENSE.txt"),
    ))
    import tkinter

    tcl = _first(*sorted(base.glob("tcl/tcl8*/license.terms")), *sorted(Path("/usr/share/tcltk").glob("tcl8*/license.terms")))
    tk = _first(*sorted(base.glob("tcl/tk8*/license.terms")), *sorted(Path("/usr/share/tcltk").glob("tk8*/license.terms")))
    out.append((f"Tcl {tkinter.TclVersion}", "Tcl/Tk licence (BSD-style)", tcl))
    out.append((f"Tk {tkinter.TkVersion}", "Tcl/Tk licence (BSD-style)", tk))
    try:
        import PyInstaller

        pkg = Path(PyInstaller.__file__).resolve().parent
        boot = _first(pkg.parent / f"pyinstaller-{PyInstaller.__version__}.dist-info" / "licenses" / "COPYING.txt",
                      pkg.parent / f"pyinstaller-{PyInstaller.__version__}.dist-info" / "COPYING.txt",
                      pkg / "COPYING.txt")
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
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
