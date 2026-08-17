import numpy as np
import pandas as pd

from experiments.mimic2_envelope_confirmation.run_confirmation import (
    WINDOW_SAMPLES,
    SegmentSpec,
    SignalSpec,
    confirmation_decision,
    decode_resp_window,
    directory_links,
    parse_segment_header,
    segment_header_is_supported,
)


def test_directory_links_are_sorted_and_unique() -> None:
    html = (
        '<a href="s00020/">b</a>'
        '<a href="other/">x</a>'
        '<a href="s00001/">a</a>'
        '<a href="s00020/">b2</a>'
    )

    assert directory_links(html, r"s\d{5}/") == ["s00001/", "s00020/"]


def test_parse_supported_format_16_resp_header() -> None:
    header = """record 2 125 60001
record.dat 16 1023(0)/pm 10 512 -32768 0 0 RESP
record.dat 16 1023(0)/NU 10 512 -32768 0 0 PLETH
"""

    segment = parse_segment_header(
        header,
        subject="s12345",
        header_file="record_0001.hea",
    )

    assert segment.resp_index == 0
    assert segment.signals[0].gain == 1023
    assert segment.signals[0].baseline == 0
    assert segment_header_is_supported(segment) == (True, "header_eligible")


def test_decode_format_16_uses_gain_baseline_and_invalid_sentinel() -> None:
    segment = SegmentSpec(
        subject="s12345",
        header_file="record_0001.hea",
        record_name="record_0001",
        signal_count=2,
        sampling_rate=125,
        sample_count=WINDOW_SAMPLES,
        signals=(
            SignalSpec("record.dat", 16, 100.0, 10, "RESP"),
            SignalSpec("record.dat", 16, 100.0, 0, "II"),
        ),
    )
    digital = np.zeros((WINDOW_SAMPLES, 2), dtype="<i2")
    digital[:, 0] = 110
    digital[4, 0] = -32_768

    respiration, valid = decode_resp_window(digital.tobytes(), segment)

    assert respiration[0] == 1.0
    assert not valid[4]
    assert valid.sum() == WINDOW_SAMPLES - 1


def test_decode_format_80_applies_offset_binary() -> None:
    segment = SegmentSpec(
        subject="s12345",
        header_file="record_0001.hea",
        record_name="record_0001",
        signal_count=1,
        sampling_rate=125,
        sample_count=WINDOW_SAMPLES,
        signals=(SignalSpec("record.dat", 80, 10.0, 0, "RESP"),),
    )
    stored = np.full(WINDOW_SAMPLES, 138, dtype=np.uint8)
    stored[2] = 0

    respiration, valid = decode_resp_window(stored.tobytes(), segment)

    assert respiration[0] == 1.0
    assert not valid[2]


def test_confirmation_decision_uses_declared_directions() -> None:
    subject_summary = pd.DataFrame(
        {
            "source_subject": ["s1", "s1", "s2", "s2"],
            "construction": [
                "envelope",
                "envelope_plateau",
                "envelope",
                "envelope_plateau",
            ],
            "featuregraph_detected_peaks": [10, 10, 12, 12],
        }
    )
    aggregate = pd.DataFrame(
        {
            "construction": ["envelope", "envelope_plateau"],
            "matched_objects": [18, 20],
            "baseline_only_objects": [4, 2],
            "median_absolute_peak_error_samples": [12.0, 5.0],
        }
    )

    decision = confirmation_decision(subject_summary, aggregate)

    assert decision["passed_all_declared_criteria"]
    assert all(decision["criteria"].values())
