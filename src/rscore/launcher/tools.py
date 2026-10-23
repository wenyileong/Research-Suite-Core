"""Tool registry, detection, saved settings and launching.

A tool is found in this order: the location the user saved with Locate; the launcher's own folder and
the folders beside it (a portable bundle); the tool's usual install folder; and, on Windows, the
install folder its installer records in the registry. Nothing is launched unless it is an existing
file, and on Windows a ``.exe``. Programs are started directly, never through a shell.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

LANGUAGES = ("en", "zh-Hans")


@dataclass(frozen=True)
class Tool:
    key: str
    exe_names: tuple[str, ...]
    #: Install folders relative to %LOCALAPPDATA% (Windows) where the tool's installer puts it.
    local_install_dirs: tuple[str, ...] = ()
    #: (registry key under HKEY_CURRENT_USER, value name) holding the install folder.
    registry: tuple[str, str] | None = None
    colour: str = "#4F46E5"
    #: Repository, for the About box and "Get it" links.
    repository: str = ""


TOOLS: tuple[Tool, ...] = (
    Tool(
        key="ashare",
        exe_names=("AShareScraper.exe",),
        local_install_dirs=("Programs/AShareScraper",),
        registry=("Software\\AShareScraper", "InstallDir"),
        colour="#EF4444",
        repository="https://github.com/wenyileong/ashare-company-intelligence",
    ),
    Tool(
        key="lab",
        exe_names=("taxnetlab.exe",),
        local_install_dirs=("Programs/International Tax Network Lab",),
        colour="#10B981",
        repository="https://github.com/wenyileong/international-tax-network-lab",
    ),
    Tool(
        key="rulebench",
        exe_names=("JAF_Rule_Bench.exe",),
        colour="#F59E0B",
        repository="https://github.com/wenyileong/jaf-rule-bench",
    ),
)
TOOLS_BY_KEY = {t.key: t for t in TOOLS}


# ------------------------------------------------------------------ settings
def default_config_path() -> Path:
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        base = Path(os.environ["APPDATA"]) / "ResearchSuite"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "research-suite"
    return base / "launcher.json"


@dataclass
class Settings:
    language: str = "en"
    tool_paths: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Settings":
        """Read saved settings. A missing file gives defaults; an unreadable one is set aside as ``.bak``."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("settings file is not a JSON object")
        except FileNotFoundError:
            return cls()
        except (OSError, ValueError):
            try:
                path.replace(path.with_suffix(".json.bak"))
            except OSError:
                pass
            return cls()
        language = data.get("language") if data.get("language") in LANGUAGES else "en"
        raw = data.get("tool_paths") if isinstance(data.get("tool_paths"), dict) else {}
        paths = {k: v for k, v in raw.items() if k in TOOLS_BY_KEY and isinstance(v, str)}
        return cls(language, paths)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        data = {"version": 1, "language": self.language, "tool_paths": self.tool_paths}
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)


# ------------------------------------------------------------------ detection
@dataclass(frozen=True)
class Found:
    path: Path
    how: str  # "saved", "beside", "installed" or "registry"


def is_program(path: Path, platform: str | None = None) -> bool:
    platform = platform or sys.platform
    if not path.is_file():
        return False
    if platform == "win32":
        return path.suffix.lower() == ".exe"
    return os.access(path, os.X_OK)


def launcher_dir() -> Path:
    """Folder of the running launcher (the exe when frozen, else this package)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _registry_dir(key: str, value: str) -> Path | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            folder, _ = winreg.QueryValueEx(k, value)
        return Path(folder)
    except OSError:
        return None


def _subdirs(folder: Path) -> list[Path]:
    try:
        return sorted(p for p in folder.iterdir() if p.is_dir())
    except OSError:
        return []


def candidates(tool: Tool, *, base: Path, local_appdata: Path | None) -> list[tuple[Path, str]]:
    """Places to look for a tool, in order, without the saved location: the launcher's folder, its
    subfolders and the folders beside it (a portable bundle), then the usual install folders."""
    out: list[tuple[Path, str]] = []
    folders = [base, *_subdirs(base), *[d for d in _subdirs(base.parent) if d != base]]
    for folder in folders:
        for name in tool.exe_names:
            out.append((folder / name, "beside"))
    if local_appdata is not None:
        for rel in tool.local_install_dirs:
            for name in tool.exe_names:
                out.append((local_appdata / rel / name, "installed"))
    if tool.registry:
        folder = _registry_dir(*tool.registry)
        if folder is not None:
            for name in tool.exe_names:
                out.append((folder / name, "registry"))
    return out


def find(tool: Tool, settings: Settings, *, base: Path | None = None, local_appdata: Path | None = None,
         platform: str | None = None) -> Found | None:
    saved = settings.tool_paths.get(tool.key)
    if saved and is_program(Path(saved), platform):
        return Found(Path(saved), "saved")
    if base is None:
        base = launcher_dir()
    if local_appdata is None and os.environ.get("LOCALAPPDATA"):
        local_appdata = Path(os.environ["LOCALAPPDATA"])
    for path, how in candidates(tool, base=base, local_appdata=local_appdata):
        if is_program(path, platform):
            return Found(path, how)
    return None


# ------------------------------------------------------------------ launching
class LaunchError(RuntimeError):
    pass


def launch(path: Path) -> subprocess.Popen:
    """Start a tool in its own folder, detached from the launcher. Console tools get their own window."""
    if not is_program(path):
        raise LaunchError(f"not a program file: {path}")
    kwargs: dict = {"cwd": str(path.parent), "close_fds": True}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        return subprocess.Popen([str(path)], **kwargs)
    except OSError as exc:
        raise LaunchError(str(exc)) from exc
