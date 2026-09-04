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


def test_missing_cohere_key_is_a_clear_exit_not_56_failures(
    tmp_path: Path, monkeypatch, capsys
):
    monkeypatch.delenv("COHERE_API_KEY", raising=False)

    code = eval_script.main(["--provider", "cohere", "--output", str(tmp_path)])

    err = capsys.readouterr().err
    assert code == 2
    assert "COHERE_API_KEY is not set" in err
    assert not (tmp_path / "cases.csv").exists()


def test_a_provider_that_becomes_unavailable_stops_the_run(tmp_path: Path, capsys):
    from featuregraph.study_builder.elicitation import ElicitorUnavailable

    class Dead:
        name = "dead"

        def complete(self, prompt, schema):
            raise ElicitorUnavailable("dead: 401 invalid api key")

    monkeypatch_target = eval_script.make_elicitor
    try:
        eval_script.make_elicitor = lambda provider, model: Dead()
        code = eval_script.main(
            ["--provider", "offline", "--output", str(tmp_path), "--full-only"]
        )
    finally:
        eval_script.make_elicitor = monkeypatch_target

    err = capsys.readouterr().err
    assert code == 2
    assert "401" in err


def test_a_failed_case_prints_its_reason(tmp_path: Path, capsys):
    class Broken:
        name = "broken"

        def complete(self, prompt, schema):
            return "not json", {"model": "broken"}

    original = eval_script.make_elicitor
    try:
        eval_script.make_elicitor = lambda provider, model: Broken()
        eval_script.main(
            ["--provider", "offline", "--output", str(tmp_path), "--full-only"]
        )
    finally:
        eval_script.make_elicitor = original

    out = capsys.readouterr().out
    assert "failed: intake:" in out
