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


def test_behavior_rejects_non_unique_source_index() -> None:
    df = pd.DataFrame(
        {"signal": [0.0, 1.0]},
        index=["sample", "sample"],
    )

    with pytest.raises(ValueError, match="index must be unique"):
        Oscillation("signal", diff_lag=1).fit_transform(df)


@pytest.mark.parametrize(
    ("time", "message"),
    [
        ([0.0, 2.0, 1.0], "strictly increasing"),
        ([0.0, float("nan"), 2.0], "missing"),
    ],
)
def test_behavior_validates_time_order(
    time: list[float],
    message: str,
) -> None:
    df = pd.DataFrame(
        {"signal": [0.0, 1.0, 2.0], "time": time}
    )

    with pytest.raises(ValueError, match=message):
        Oscillation(
            "signal",
            diff_lag=1,
            time="time",
        ).fit_transform(df)
