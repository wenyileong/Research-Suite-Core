"""Safeguards that keep the window complete as the suite grows (docs/interface_guidelines.md).

1. Every command of ``python -m rscore`` is a service and has an action in the window.
2. Every text key the window uses exists in every language, with the same placeholders.
3. Every rejection reason the importer can give has a plain-language label in every language.
4. Where a display is available, the window's own self-test builds every page in both languages and runs
   the example import end to end (the Windows build runs the same self-test on the packaged exe).
"""

import argparse
import re
from pathlib import Path

import pytest

tk = pytest.importorskip("tkinter", reason="this Python has no Tk; the CI and Windows builds have it")

from rscore import __main__ as cli
from rscore import conventions as cv
from rscore import schema as sc
from rscore import services
from rscore.launcher import app, i18n
from rscore.launcher import tools as tl

SRC = Path(__file__).resolve().parents[1] / "src" / "rscore"
APP_SRC = (SRC / "launcher" / "app.py").read_text(encoding="utf-8")
IMPORTER_SRC = (SRC / "importers" / "ashare.py").read_text(encoding="utf-8")


def cli_commands() -> set[str]:
    parser = argparse.ArgumentParser()
    original = argparse.ArgumentParser.parse_args
    seen = {}

    def capture(self, args=None, namespace=None):
        for action in self._actions:
            if isinstance(action, argparse._SubParsersAction):
                seen["commands"] = set(action.choices)
        raise SystemExit(0)

    argparse.ArgumentParser.parse_args = capture
    try:
        with pytest.raises(SystemExit):
            cli.main(["validate"])
    finally:
        argparse.ArgumentParser.parse_args = original
    del parser
    return seen["commands"]


def test_every_command_is_a_service_and_a_window_action():
    assert cli_commands() == set(services.COMMANDS)
    assert set(app.GUI_ACTIONS) == set(services.COMMANDS)
    for command, (page, method) in app.GUI_ACTIONS.items():
        assert page in app.PAGES, command
        assert callable(getattr(app.PAGE_CLASSES[page], method, None)), f"{command}: {page}.{method} missing"


def test_every_page_has_a_class_and_text():
    assert set(app.PAGES) == set(app.PAGE_CLASSES)
    for key in app.PAGES:
        for prefix in ("nav_", "title_", "intro_"):
            assert prefix + key in i18n.EN


def keys_used() -> set[str]:
    # Literal keys; prefixes such as "rel_" + value are expanded below.
    keys = {k for k in re.findall(r'\.t\(\s*"([a-z_]+)"', APP_SRC) if not k.endswith("_")}
    keys |= set(re.findall(r'\("[a-z_]+", "(col_[a-z_]+)", \d+, "[we]"\)', APP_SRC))
    keys |= {f"{p}{k}" for k in app.PAGES for p in ("nav_", "title_", "intro_")}
    keys |= {f"table_{t}" for t in sc.CONTENT_TABLES}
    keys |= {f"table_{t}" for t in ("ownership_observations", "subsidiary_observations", "control_observations",
                                    "control_edges", "financial_facts")}
    keys |= {f"tabledesc_{t}" for t in services.SUMMARY_TABLES}
    keys |= {f"rel_{r}" for r in cv.RELATION_TYPES} | {f"basis_{c}" for c in cv.CONSOLIDATION}
    keys |= {"level_error", "level_warning", "opt_assume_help", "opt_accept_help", "opt_assume", "opt_accept"}
    keys |= {f"problem_place_{s}" for s in ("unmatched", "ambiguous", "missing", "empty")}
    keys |= {f"progress_{m.replace(' ', '_')}" for m in re.findall(r'say\("([a-z ]+)"\)',
                                                                    (SRC / "services.py").read_text())}
    keys |= {f"stat_{s}" for s in ("entities", "relations", "revenue", "rejected")}
    keys |= {f"step_{s}" for s in ("project", "import", "review", "lab")}
    keys |= {f"{tool.key}_{s}" for tool in tl.TOOLS for s in ("name", "desc")}
    return keys


def test_every_text_key_exists_in_every_language():
    placeholders = re.compile(r"{(\w+)}")
    used = keys_used()
    for lang in tl.LANGUAGES:
        table = i18n.STRINGS[lang]
        missing = sorted(used - set(table))
        assert not missing, f"{lang} lacks {missing}"
        assert set(table) == set(i18n.EN), lang
        for key, value in table.items():
            assert set(placeholders.findall(value)) == set(placeholders.findall(i18n.EN[key])), (lang, key)
            assert "—" not in value and "–" not in value, (lang, key)


def test_every_rejection_reason_has_a_label():
    reasons = set(re.findall(r'reject\([^()]*?"([a-z0-9_]+)"\)', IMPORTER_SRC))
    reasons |= {f"place_{s}" for s in ("unmatched", "ambiguous")}
    assert len(reasons) > 10
    for lang in tl.LANGUAGES:
        missing = sorted(reasons - set(i18n.REASONS[lang]))
        assert not missing, f"{lang} lacks reason labels {missing}"


def _display() -> bool:
    try:
        root = tk.Tk()
    except tk.TclError:
        return False
    root.destroy()
    return True


@pytest.mark.skipif(not _display(), reason="no display (the Windows build runs this on the packaged exe)")
def test_window_self_test(tmp_path):
    app.self_test(tmp_path / "launcher.json")


def test_packaging_includes_every_data_file():
    spec = (SRC.parents[1] / "packaging" / "research_suite.spec").read_text(encoding="utf-8")
    assert 'glob("*.json")' in spec and '"rscore" / "data"' in spec
    assert 'ASSETS.glob("*.png")' in spec
    for path in (SRC / "data").iterdir():
        assert path.suffix == ".json", f"{path.name}: the spec packs only .json files from src/rscore/data"


def test_self_test_reports_failure_without_a_dialog(tmp_path, monkeypatch):
    from rscore.launcher import __main__ as launcher_main

    def broken(_config):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(app, "self_test", broken)
    log = tmp_path / "log.txt"
    assert launcher_main.main(["--self-test", "--log", str(log)]) == 1
    assert "simulated failure" in log.read_text(encoding="utf-8")
