import pytest

from rscore import demo, services


@pytest.fixture
def project(tmp_path):
    return services.create_project(tmp_path / "study")


@pytest.fixture
def release(tmp_path):
    return demo.build(tmp_path / "example_release")


def test_create_project(project):
    assert project.path.suffix == ".sqlite" and project.path.exists()
    s = services.summary(project)
    assert s["jurisdictions"] == 250 and s["entities"] == 0
    assert project.files.name == "study_files"


def test_import_writes_report_into_project(project, release):
    res = services.run_import(project, release)
    assert res.report_dir.parent == project.files / "import_reports"
    assert (res.report_dir / "import_report.md").exists()
    assert services.report_settings(res.report_dir)["release_folder"].endswith("example_release")
    assert services.latest_report(project) == res.report_dir
    assert services.summary(project)["ownership"] == 5


def test_review_loop(project, release):
    res = services.run_import(project, release)
    items = {i.name: i for i in services.load_review(res.report_dir, project)}
    assert items["香港中央结算有限公司"].suggestion == "HKG" and items["香港中央结算有限公司"].chosen == ""
    services.save_overrides(project, {"香港中央结算有限公司": "hkg", "欧洲": "DEU"})
    with pytest.raises(ValueError):
        services.save_overrides(project, {"维尔京群岛": "ZZZ"})
    res2 = services.run_import(project, release)
    items = {i.name: i for i in services.load_review(res2.report_dir, project)}
    assert "香港中央结算有限公司" not in items and "欧洲" not in items
    assert services.summary(project)["ownership"] == 7
    services.save_overrides(project, {"欧洲": ""})
    assert "欧洲" not in services.load_overrides(project)


def test_revenue_conflicts(project, release):
    res = services.run_import(project, release, assume_consolidated=True)
    conflicts = services.load_revenue_conflicts(res.report_dir)
    assert conflicts[0]["security_code"] == "DEMO02"


def test_browse(project, release):
    services.run_import(project, release)
    rows = services.ownership_rows(project)
    assert any(r["held_j"] == "CYM" for r in rows)
    assert all(r["source_url"] for r in rows if r["relation_type"] == "equity")
    assert services.ownership_rows(project, "开曼") and not services.ownership_rows(project, "no such name")
    assert services.revenue_rows(project)[0]["operating_revenue"] == 1.5e10


def test_lab_snapshot_check(project, release):
    services.run_import(project, release)
    out = services.export_lab(project)
    assert (out / "ownership.csv").exists()
    folder = services.take_snapshot(project, "first")
    assert services.verify_snapshot(folder) == []
    snaps = services.list_snapshots(project)
    assert snaps[0]["note"] == "first" and snaps[0]["counts"]["ownership"] == 5
    assert services.snapshot_folder(project, snaps[0]["snapshot_id"]) == folder
    assert services.check(project).ok


def test_open_url_refuses_non_web():
    assert services.open_url("file:///C:/Windows/system32/calc.exe") is False
    assert services.open_url(None) is False
