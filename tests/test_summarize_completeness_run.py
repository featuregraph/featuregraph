"""The run summariser reduces case records to headline counts and a field table."""

from pathlib import Path

import pandas as pd

from scripts import completeness_disagreement as eval_script
from scripts import summarize_completeness_run as summarize


def test_offline_run_summarises_to_zero_disagreement(tmp_path: Path, capsys):
    eval_script.main(
        [
            "--provider",
            "offline",
            "--output",
            str(tmp_path),
            "--only",
            "physionet_wearable",
        ]
    )

    code = summarize.main([str(tmp_path)])

    out = capsys.readouterr().out
    assert code == 0
    head = summarize.headline(summarize.load_records(tmp_path))
    assert head["failed"] == 0 and head["exact_agreement"] == head["cases"]
    assert head["fabricated"] == 0 and head["false_ready"] == 0
    # The honest offline elicitor declares nothing, so every field is
    # outstanding in every case and is named every time.
    fields = pd.read_csv(tmp_path / "fields.csv")
    assert (fields["outstanding"] == fields["cases"]).all()
    assert (fields["outstanding_and_named"] == fields["outstanding"]).all()
    withheld = pd.read_csv(tmp_path / "withheld.csv")
    assert withheld["left_unset"].all() and withheld["named_missing"].all()
    assert "exact_agreement" in out


def test_missing_records_is_an_error(tmp_path: Path):
    import pytest

    with pytest.raises(FileNotFoundError):
        summarize.load_records(tmp_path)
