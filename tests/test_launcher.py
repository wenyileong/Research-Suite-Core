import json
import re
import stat

import pytest

from rscore.launcher import i18n
from rscore.launcher import tools as tl


def make_program(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_settings_round_trip(tmp_path):
    cfg = tmp_path / "sub" / "launcher.json"
    s = tl.Settings(language="zh-Hans", tool_paths={"lab": "C:/x/taxnetlab.exe"})
    s.save(cfg)
    loaded = tl.Settings.load(cfg)
    assert loaded == s
    assert json.loads(cfg.read_text(encoding="utf-8"))["version"] == 1


def test_settings_missing_or_bad(tmp_path):
    assert tl.Settings.load(tmp_path / "none.json") == tl.Settings()
    bad = tmp_path / "launcher.json"
    bad.write_text("{not json", encoding="utf-8")
    assert tl.Settings.load(bad) == tl.Settings()
    assert (tmp_path / "launcher.json.bak").exists()


def test_settings_ignore_unknown_values(tmp_path):
    cfg = tmp_path / "launcher.json"
    cfg.write_text(json.dumps({"language": "fr", "tool_paths": {"lab": "a", "evil": "b", "ashare": 3}}))
    s = tl.Settings.load(cfg)
    assert s.language == "en" and s.tool_paths == {"lab": "a"}


def test_windows_requires_exe(tmp_path):
    exe = make_program(tmp_path / "tool.exe")
    other = make_program(tmp_path / "tool.bat")
    assert tl.is_program(exe, "win32")
    assert not tl.is_program(other, "win32")
    assert not tl.is_program(tmp_path / "missing.exe", "win32")


def test_find_order(tmp_path):
    lab = tl.TOOLS_BY_KEY["lab"]
    base = tmp_path / "bundle" / "ResearchSuite"
    base.mkdir(parents=True)
    local = tmp_path / "local"
    installed = make_program(local / "Programs" / "International Tax Network Lab" / "taxnetlab.exe")
    found = tl.find(lab, tl.Settings(), base=base, local_appdata=local, platform="linux")
    assert found == tl.Found(installed, "installed")

    beside = make_program(tmp_path / "bundle" / "TaxNetLab" / "taxnetlab.exe")
    found = tl.find(lab, tl.Settings(), base=base, local_appdata=local, platform="linux")
    assert found == tl.Found(beside, "beside")

    saved = make_program(tmp_path / "elsewhere" / "taxnetlab.exe")
    found = tl.find(lab, tl.Settings(tool_paths={"lab": str(saved)}), base=base, local_appdata=local,
                    platform="linux")
    assert found == tl.Found(saved, "saved")


def test_saved_location_that_vanished_falls_back(tmp_path):
    lab = tl.TOOLS_BY_KEY["lab"]
    settings = tl.Settings(tool_paths={"lab": str(tmp_path / "gone" / "taxnetlab.exe")})
    assert tl.find(lab, settings, base=tmp_path, local_appdata=None, platform="linux") is None


def test_subfolder_of_launcher_is_searched(tmp_path):
    rb = tl.TOOLS_BY_KEY["rulebench"]
    exe = make_program(tmp_path / "ResearchSuite" / "tools" / "JAF_Rule_Bench.exe")
    found = tl.find(rb, tl.Settings(), base=tmp_path / "ResearchSuite", local_appdata=None, platform="linux")
    assert found == tl.Found(exe, "beside")


def test_launch_refuses_non_programs(tmp_path):
    with pytest.raises(tl.LaunchError):
        tl.launch(tmp_path / "missing.exe")


def test_every_language_has_every_string():
    placeholders = re.compile(r"{(\w+)}")
    for lang in tl.LANGUAGES:
        table = i18n.STRINGS[lang]
        assert set(table) == set(i18n.EN), lang
        for key, value in table.items():
            assert set(placeholders.findall(value)) == set(placeholders.findall(i18n.EN[key])), (lang, key)
    for tool in tl.TOOLS:
        assert f"{tool.key}_name" in i18n.EN and f"{tool.key}_desc" in i18n.EN


def test_no_dashes_in_interface_text():
    for table in i18n.STRINGS.values():
        for value in table.values():
            assert "\u2014" not in value and "\u2013" not in value
