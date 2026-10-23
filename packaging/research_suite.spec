# PyInstaller specification for ResearchSuite.exe, the suite launcher.
# Build from the repository root:  pyinstaller --noconfirm --clean packaging\research_suite.spec
# One file, no console window. The launcher uses the standard library only (tkinter included).

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT / "src"))
from rscore import __version__  # noqa: E402

ASSETS = ROOT / "src" / "rscore" / "launcher" / "assets"
datas = [(str(p), "rscore/launcher/assets") for p in sorted(ASSETS.glob("*.png"))]
datas.append((str(ROOT / "src" / "rscore" / "data" / "iso3166.json"), "rscore/data"))


def _version_resource():
    """Windows file properties (version, product name, copyright), generated from rscore.__version__."""
    if sys.platform != "win32":
        return None
    from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                      VarFileInfo, VarStruct, VSVersionInfo)
    parts = tuple(int(p) for p in __version__.split(".")[:3]) + (0,)
    strings = [
        StringStruct("CompanyName", "Leong, Wen Yi"),
        StringStruct("FileDescription", "Research Suite launcher"),
        StringStruct("FileVersion", __version__),
        StringStruct("InternalName", "ResearchSuite"),
        StringStruct("LegalCopyright", "Copyright (c) 2026 Leong, Wen Yi. All rights reserved."),
        StringStruct("OriginalFilename", "ResearchSuite.exe"),
        StringStruct("ProductName", "Research Suite"),
        StringStruct("ProductVersion", __version__),
    ]
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=parts, prodvers=parts),
        kids=[StringFileInfo([StringTable("080904B0", strings)]), VarFileInfo([VarStruct("Translation", [2057, 1200])])],
    )


a = Analysis(
    [str(ROOT / "packaging" / "launcher_entry.py")],
    pathex=[str(ROOT / "src")],
    datas=datas,
    hiddenimports=[],
    excludes=["numpy", "pandas", "matplotlib", "PIL", "pytest", "IPython", "unittest", "pydoc_data"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="ResearchSuite",
    icon=str(ROOT / "packaging" / "research_suite.ico"),
    version=_version_resource(),
    console=False,
    upx=False,
)
