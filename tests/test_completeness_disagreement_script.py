"""The eval script runs offline end to end and writes one row per case."""

import json
from pathlib import Path

import pandas as pd

from scripts import completeness_disagreement as eval_script


def test_offline_run_writes_cases_and_summary(tmp_path: Path, capsys):
    code = eval_script.main(
        [
            "--provider",
            "offline",
            "--output",
            str(tmp_path),
            "--only",
            "tep_reactor_pressure",
        ]
    )

    out = capsys.readouterr().out
    assert code == 0
    table = pd.read_csv(tmp_path / "cases.csv")
    assert (table["reference"] == "tep_reactor_pressure").all()
    assert (table["case_id"] == "tep_reactor_pressure/full").any()
    # The honest offline elicitor declares nothing and says so: never wrong.
    assert table["agrees_exactly"].all()
    assert (table["fabricated"] == 0).all()
    assert not table["failed"].any()
    assert "exact agreement" in out
    record = json.loads(
        (tmp_path / "cases" / "tep_reactor_pressure__full.json").read_text()
    )
    assert record["claim"]["authoritative"] is False
    assert record["score"]["derived"]["unset"]


def test_full_only_skips_ablations(tmp_path: Path):
    eval_script.main(
        ["--provider", "offline", "--output", str(tmp_path), "--full-only"]
    )
    table = pd.read_csv(tmp_path / "cases.csv")

    assert (table["withheld"].fillna("") == "").all()
    assert len(table) == len(eval_script.load_references())
