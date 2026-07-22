import pandas as pd
import pytest

from featuregraph.behaviors.oscillation import Oscillation


def test_constructor_normalizes_signal_and_group_names() -> None:
    behavior = Oscillation(
        signals="signal",
        group="subject",
    )

    assert behavior.signals == ["signal"]
    assert behavior.group_columns == ["subject"]
    assert behavior.object_group("signal", "wave_id") == [
        "subject",
        "signal_wave_id",
    ]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"signals": []}, "At least one signal"),
        ({"signals": "x", "smooth_window": 0}, "smooth_window"),
        ({"signals": "x", "diff_lag": 0}, "diff_lag"),
        ({"signals": "x", "eps": -1}, "eps"),
    ],
)
def test_oscillation_rejects_invalid_configuration(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        Oscillation(**kwargs)


def test_fit_transform_rejects_missing_columns() -> None:
    behavior = Oscillation("signal", group="subject")

    with pytest.raises(ValueError, match="subject"):
        behavior.fit_transform(pd.DataFrame({"signal": [1.0]}))
