"""The held-out runner's check mode: comparison and provenance, without data.

The construction itself needs PhysioNet. These tests cover what surrounds it:
that a byte-identical output is reported identical, that a changed one is
not, and that the provenance record names what it must.
"""

import json
from pathlib import Path

import pytest

from scripts import run_bidmc_multiscale_heldout as runner


@pytest.fixture
def committed(tmp_path: Path) -> Path:
    directory = tmp_path / "committed"
    directory.mkdir()
    (directory / "subject_summary.csv").write_text("subject,value\n1,2\n")
    (directory / "report.md").write_text("# report\n")
    return directory


def _copy(source: Path, target: Path) -> Path:
    target.mkdir()
    for name in runner.OUTPUT_FILES:
        (target / name).write_bytes((source / name).read_bytes())
    return target


def test_identical_outputs_compare_identical(committed: Path, tmp_path: Path):
    produced = _copy(committed, tmp_path / "produced")

    check = runner.compare(produced, committed)

    assert check["identical"] is True
    assert all(entry["identical"] for entry in check["files"].values())
    assert set(check["files"]) == set(runner.OUTPUT_FILES)


def test_one_changed_byte_is_reported_by_file(committed: Path, tmp_path: Path):
    produced = _copy(committed, tmp_path / "produced")
    (produced / "subject_summary.csv").write_text("subject,value\n1,3\n")

    check = runner.compare(produced, committed)

    assert check["identical"] is False
    assert check["files"]["subject_summary.csv"]["identical"] is False
    assert check["files"]["report.md"]["identical"] is True


def test_missing_committed_file_is_not_identical(committed: Path, tmp_path: Path):
    produced = _copy(committed, tmp_path / "produced")
    (committed / "report.md").unlink()

    check = runner.compare(produced, committed)

    assert check["files"]["report.md"]["committed"] is None
    assert check["identical"] is False


def test_provenance_names_commit_versions_and_hashes(committed: Path):
    record = runner.provenance(committed, check={"identical": True})

    assert set(record["outputs"]) == set(runner.OUTPUT_FILES)
    assert len(record["outputs"]["subject_summary.csv"]) == 64
    for key in (
        "git_commit",
        "git_tree_clean",
        "featuregraph_version",
        "python_version",
        "numpy_version",
        "pandas_version",
        "scipy_version",
        "run_at",
    ):
        assert key in record
    assert record["check"] == {"identical": True}
    json.dumps(record)  # serialisable as written


def test_check_mode_exits_nonzero_on_difference(committed: Path, monkeypatch):
    """Check mode runs the construction into a temporary directory and compares."""

    def fake_run(output: Path) -> None:
        (output / "subject_summary.csv").write_text("subject,value\n1,999\n")
        (output / "report.md").write_text("# report\n")

    monkeypatch.setattr(runner, "run", fake_run)

    code = runner.main(["--check", "--output-dir", str(committed)])

    assert code == 1
    record = json.loads((committed / "provenance.json").read_text())
    assert record["check"]["identical"] is False
    # The committed outputs were not touched by the check.
    assert (committed / "subject_summary.csv").read_text() == "subject,value\n1,2\n"


def test_check_mode_exits_zero_when_identical(committed: Path, monkeypatch):
    def fake_run(output: Path) -> None:
        for name in runner.OUTPUT_FILES:
            (output / name).write_bytes((committed / name).read_bytes())

    monkeypatch.setattr(runner, "run", fake_run)

    assert runner.main(["--check", "--output-dir", str(committed)]) == 0
    record = json.loads((committed / "provenance.json").read_text())
    assert record["check"]["identical"] is True


def test_numerics_download_retries_a_gateway_error(tmp_path: Path, monkeypatch):
    """One transient failure from PhysioNet must not end the run."""
    import urllib.error

    monkeypatch.setattr(runner, "CACHE", tmp_path)
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    calls: list[str] = []

    def flaky_urlretrieve(url: str, path: Path) -> None:
        calls.append(url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(url, 502, "Bad Gateway", {}, None)
        Path(path).write_text("Time [s], HR, PULSE\n0,90,91\n")

    monkeypatch.setattr(runner, "urlretrieve", flaky_urlretrieve)

    numerics = runner.load_numerics({"BASE": "https://example.invalid/bidmc"}, 7)

    assert calls == ["https://example.invalid/bidmc/bidmc_07_Numerics.csv"] * 2
    assert numerics["HR"].tolist() == [90]


def test_numerics_download_gives_up_after_the_last_attempt(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(runner, "CACHE", tmp_path)
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)

    def broken_urlretrieve(url: str, path: Path) -> None:
        raise OSError("connection reset")

    monkeypatch.setattr(runner, "urlretrieve", broken_urlretrieve)

    with pytest.raises(RuntimeError, match="after 4 attempts"):
        runner.load_numerics({"BASE": "https://example.invalid/bidmc"}, 7)
    assert not (tmp_path / "bidmc_07_Numerics.csv").exists()
