"""Run the frozen envelope/plateau rule on untouched MIMIC-II windows."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from experiments.bidmc_llm_capture.compare_object_tables import (
    comparison_summary,
    match_ordered_objects,
)
from experiments.bidmc_llm_capture.multi_subject_comparison import (
    PEAK_TOLERANCE_SAMPLES,
    native_featuregraph_objects,
)
from experiments.bidmc_llm_capture.reproduce_llm_method import reproduce

SOURCE_BASE_URL = (
    "https://physionet.org/physiobank/database/mimic2wdb/matched"
)
BIDMC_FIX_BASE_URL = (
    "https://physionet.org/files/bidmc/1.0.0/bidmc_csv"
)
SAMPLING_RATE = 125
WINDOW_SAMPLES = 60_001
TARGET_SUBJECTS = 20
SUPPORTED_FORMATS = {16, 80}
USER_AGENT = "FeatureGraph-MIMIC2-confirmation/1.0"


@dataclass(frozen=True)
class SignalSpec:
    """One signal line from a simple WFDB header."""

    data_file: str
    sample_format: int
    gain: float
    baseline: int
    description: str


@dataclass(frozen=True)
class SegmentSpec:
    """A simple, fixed-layout WFDB segment eligible for range reading."""

    subject: str
    header_file: str
    record_name: str
    signal_count: int
    sampling_rate: float
    sample_count: int
    signals: tuple[SignalSpec, ...]

    @property
    def resp_index(self) -> int:
        """Return the exact RESP channel position."""
        return next(
            index
            for index, signal in enumerate(self.signals)
            if signal.description == "RESP"
        )

    @property
    def sample_format(self) -> int:
        """Return the shared sample format."""
        return self.signals[0].sample_format

    @property
    def data_file(self) -> str:
        """Return the shared data filename."""
        return self.signals[0].data_file


@dataclass
class SelectedWindow:
    """One prospectively selected confirmation window."""

    segment: SegmentSpec
    respiration: np.ndarray = field(repr=False)
    raw_sha256: str


class CachedHttpClient:
    """Small retrying HTTP client with content-addressed local caching."""

    def __init__(
        self,
        cache_directory: Path,
        *,
        retries: int = 4,
        timeout_seconds: int = 60,
    ) -> None:
        self.cache_directory = cache_directory
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        self.retries = retries
        self.timeout_seconds = timeout_seconds

    def get_bytes(
        self,
        url: str,
        *,
        byte_range: tuple[int, int] | None = None,
    ) -> bytes:
        """Return a URL response, aborting after deterministic retries."""
        key = url
        if byte_range is not None:
            key = f"{key}|bytes={byte_range[0]}-{byte_range[1]}"
        digest = hashlib.sha256(key.encode()).hexdigest()
        cached = self.cache_directory / digest
        if cached.exists():
            return cached.read_bytes()

        headers = {"User-Agent": USER_AGENT}
        if byte_range is not None:
            headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
        request = urllib.request.Request(url, headers=headers)
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout_seconds,
                ) as response:
                    content = response.read()
                if byte_range is not None:
                    expected = byte_range[1] - byte_range[0] + 1
                    if len(content) != expected:
                        raise ValueError(
                            f"Range response for {url} had {len(content)} "
                            f"bytes; expected {expected}."
                        )
                cached.write_bytes(content)
                return content
            except (OSError, urllib.error.URLError, ValueError) as error:
                last_error = error
                if attempt + 1 < self.retries:
                    time.sleep(2**attempt)
        raise RuntimeError(f"Unable to fetch {url}") from last_error

    def get_text(self, url: str) -> str:
        """Return UTF-8 text with replacement for archival metadata."""
        return self.get_bytes(url).decode("utf-8", errors="replace")


def directory_links(index_html: str, pattern: str) -> list[str]:
    """Return sorted unique href values matching a full regex pattern."""
    links = re.findall(r'href="([^"]+)"', index_html)
    return sorted({link for link in links if re.fullmatch(pattern, link)})


def parse_sampling_rate(token: str) -> float:
    """Parse the leading WFDB sampling-frequency component."""
    return float(token.split("/", maxsplit=1)[0])


def parse_gain(token: str, adc_zero: int) -> tuple[float, int]:
    """Parse WFDB gain and optional baseline from a gain token."""
    match = re.match(
        r"^(?P<gain>[+-]?(?:\d+(?:\.\d*)?|\.\d+))"
        r"(?:\((?P<baseline>[+-]?\d+)\))?",
        token,
    )
    if match is None:
        raise ValueError(f"Unsupported WFDB gain token: {token}")
    gain = float(match.group("gain"))
    if gain == 0:
        raise ValueError("WFDB gain cannot be zero")
    baseline = (
        int(match.group("baseline"))
        if match.group("baseline") is not None
        else adc_zero
    )
    return gain, baseline


def parse_segment_header(
    text: str,
    *,
    subject: str,
    header_file: str,
) -> SegmentSpec:
    """Parse a simple fixed-layout WFDB header used by this experiment."""
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not lines:
        raise ValueError("WFDB header is empty")
    record_fields = lines[0].split()
    if len(record_fields) < 4:
        raise ValueError("WFDB record line has fewer than four fields")
    if "/" in record_fields[0]:
        raise ValueError("Multi-segment master headers are not eligible")

    signal_count = int(record_fields[1])
    sampling_rate = parse_sampling_rate(record_fields[2])
    sample_count = int(record_fields[3])
    signal_lines = lines[1 : signal_count + 1]
    if len(signal_lines) != signal_count:
        raise ValueError("WFDB header does not contain every signal line")

    signals: list[SignalSpec] = []
    for line in signal_lines:
        fields = line.split()
        if len(fields) < 9:
            raise ValueError("WFDB signal line has fewer than nine fields")
        if not fields[1].isdigit():
            raise ValueError(f"Unsupported WFDB format token: {fields[1]}")
        sample_format = int(fields[1])
        adc_zero = int(fields[4])
        gain, baseline = parse_gain(fields[2], adc_zero)
        description = " ".join(fields[8:]).strip().rstrip(",")
        signals.append(
            SignalSpec(
                data_file=fields[0],
                sample_format=sample_format,
                gain=gain,
                baseline=baseline,
                description=description,
            )
        )

    return SegmentSpec(
        subject=subject,
        header_file=header_file,
        record_name=record_fields[0],
        signal_count=signal_count,
        sampling_rate=sampling_rate,
        sample_count=sample_count,
        signals=tuple(signals),
    )


def segment_header_is_supported(segment: SegmentSpec) -> tuple[bool, str]:
    """Apply the frozen header-level eligibility contract."""
    if segment.sampling_rate != SAMPLING_RATE:
        return False, "sampling_rate_not_125_hz"
    if segment.sample_count < WINDOW_SAMPLES:
        return False, "segment_shorter_than_window"
    if not any(signal.description == "RESP" for signal in segment.signals):
        return False, "no_exact_resp_channel"
    formats = {signal.sample_format for signal in segment.signals}
    if len(formats) != 1 or not formats.issubset(SUPPORTED_FORMATS):
        return False, "nonuniform_or_unsupported_sample_format"
    data_files = {signal.data_file for signal in segment.signals}
    if len(data_files) != 1:
        return False, "multiple_data_files"
    return True, "header_eligible"


def decode_resp_window(
    raw: bytes,
    segment: SegmentSpec,
) -> tuple[np.ndarray, np.ndarray]:
    """Decode one interleaved WFDB window and return values and validity."""
    if segment.sample_format == 16:
        digital = np.frombuffer(raw, dtype="<i2").astype(np.int32)
        invalid_value = -32_768
    elif segment.sample_format == 80:
        digital = np.frombuffer(raw, dtype=np.uint8).astype(np.int32) - 128
        invalid_value = -128
    else:
        raise ValueError(f"Unsupported sample format: {segment.sample_format}")

    expected = WINDOW_SAMPLES * segment.signal_count
    if digital.size != expected:
        raise ValueError(
            f"Decoded {digital.size} values; expected {expected}."
        )
    matrix = digital.reshape(WINDOW_SAMPLES, segment.signal_count)
    resp = matrix[:, segment.resp_index]
    valid = resp != invalid_value
    spec = segment.signals[segment.resp_index]
    physical = (resp.astype(float) - spec.baseline) / spec.gain
    return physical, valid


def read_first_window(
    client: CachedHttpClient,
    segment: SegmentSpec,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Range-read the first eight-minute window from an eligible segment."""
    bytes_per_value = 2 if segment.sample_format == 16 else 1
    byte_count = WINDOW_SAMPLES * segment.signal_count * bytes_per_value
    url = f"{SOURCE_BASE_URL}/{segment.subject}/{segment.data_file}"
    raw = client.get_bytes(url, byte_range=(0, byte_count - 1))
    respiration, valid = decode_resp_window(raw, segment)
    return respiration, valid, hashlib.sha256(raw).hexdigest()


def bidmc_subject_ids(
    client: CachedHttpClient,
    *,
    jobs: int,
) -> list[str]:
    """Return source subject IDs used by the 53 curated BIDMC records."""
    def read_one(subject: int) -> str:
        url = f"{BIDMC_FIX_BASE_URL}/bidmc_{subject:02d}_Fix.txt"
        text = client.get_text(url)
        match = re.search(r"MIMIC II matched wdb ID:\s*(s\d+)", text)
        if match is None:
            raise ValueError(f"No MIMIC-II subject ID in {url}")
        return match.group(1)

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        identifiers = list(executor.map(read_one, range(1, 54)))
    return sorted(set(identifiers))


def candidate_subject_ids(client: CachedHttpClient) -> list[str]:
    """Return all source subject directories in lexical order."""
    index = client.get_text(f"{SOURCE_BASE_URL}/")
    return directory_links(index, r"s\d{5}/")


def inspect_subject(
    client: CachedHttpClient,
    subject: str,
) -> tuple[SelectedWindow | None, str]:
    """Return the first eligible segment for one source subject."""
    subject = subject.rstrip("/")
    index = client.get_text(f"{SOURCE_BASE_URL}/{subject}/")
    layout_files = directory_links(index, r"[^/]+_layout\.hea")
    if not layout_files:
        return None, "no_layout_headers"

    resp_families: list[str] = []
    for layout_file in layout_files:
        text = client.get_text(
            f"{SOURCE_BASE_URL}/{subject}/{layout_file}"
        )
        descriptions = [
            line.split()[-1].rstrip(",")
            for line in text.splitlines()[1:]
            if line.strip() and not line.startswith("#")
        ]
        if "RESP" in descriptions:
            resp_families.append(layout_file.removesuffix("_layout.hea"))
    if not resp_families:
        return None, "no_resp_layout"

    last_reason = "no_segment_headers"
    for family in sorted(resp_families):
        pattern = rf"{re.escape(family)}_\d+\.hea"
        segment_files = directory_links(index, pattern)
        for header_file in segment_files:
            text = client.get_text(
                f"{SOURCE_BASE_URL}/{subject}/{header_file}"
            )
            try:
                segment = parse_segment_header(
                    text,
                    subject=subject,
                    header_file=header_file,
                )
            except ValueError:
                last_reason = "unsupported_header_syntax"
                continue
            supported, reason = segment_header_is_supported(segment)
            if not supported:
                last_reason = reason
                continue
            respiration, valid, digest = read_first_window(client, segment)
            if not valid.all():
                last_reason = "invalid_resp_samples_in_first_window"
                continue
            return (
                SelectedWindow(
                    segment=segment,
                    respiration=respiration,
                    raw_sha256=digest,
                ),
                "selected",
            )
    return None, last_reason


def discover_cohort(
    client: CachedHttpClient,
    *,
    target_subjects: int,
    jobs: int,
) -> tuple[list[SelectedWindow], pd.DataFrame, list[str]]:
    """Apply the prospective cohort-selection contract."""
    excluded = bidmc_subject_ids(client, jobs=jobs)
    excluded_set = set(excluded)
    source_subjects = [
        subject.rstrip("/")
        for subject in candidate_subject_ids(client)
        if subject.rstrip("/") not in excluded_set
    ]

    selected: list[SelectedWindow] = []
    audit_rows: list[dict[str, object]] = []
    for subject in source_subjects:
        window, reason = inspect_subject(client, subject)
        audit_rows.append(
            {
                "subject": subject,
                "status": reason,
                "selected_rank": (
                    len(selected) + 1 if window is not None else pd.NA
                ),
                "header_file": (
                    window.segment.header_file if window is not None else pd.NA
                ),
            }
        )
        if window is not None:
            selected.append(window)
        print(
            f"considered={len(audit_rows)} selected={len(selected)} "
            f"subject={subject} status={reason}",
            flush=True,
        )
        if len(selected) == target_subjects:
            break

    if len(selected) != target_subjects:
        raise RuntimeError(
            f"Found {len(selected)} eligible subjects; "
            f"required {target_subjects}."
        )
    return selected, pd.DataFrame(audit_rows), excluded


def attach_source_columns(
    table: pd.DataFrame,
    window: SelectedWindow,
    construction: str,
) -> pd.DataFrame:
    """Attach stable source identity to an object-level result table."""
    result = table.copy()
    result.insert(0, "construction", construction)
    result.insert(0, "source_record", window.segment.record_name)
    result.insert(0, "source_subject", window.segment.subject)
    return result


def compare_window(
    window: SelectedWindow,
    construction: str,
) -> dict[str, pd.DataFrame | pd.Series]:
    """Run one frozen FeatureGraph construction and the SciPy comparator."""
    observations = pd.DataFrame(
        {
            "subject": window.segment.subject,
            "respiration": window.respiration,
        }
    )
    featuregraph, detected_peaks = native_featuregraph_objects(
        observations,
        construction=construction,
    )
    baseline = reproduce(observations[["respiration"]])
    matched, featuregraph_only, baseline_only = match_ordered_objects(
        featuregraph,
        baseline,
        peak_tolerance_samples=PEAK_TOLERANCE_SAMPLES,
    )
    summary = comparison_summary(matched, featuregraph_only, baseline_only)
    summary["source_subject"] = window.segment.subject
    summary["source_record"] = window.segment.record_name
    summary["header_file"] = window.segment.header_file
    summary["construction"] = construction
    summary["samples"] = WINDOW_SAMPLES
    summary["featuregraph_detected_peaks"] = len(detected_peaks)
    summary["featuregraph_partial_objects"] = int(
        (~featuregraph["is_complete"]).sum()
    )
    summary["featuregraph_ambiguous_objects"] = int(
        featuregraph.get(
            "plateau_boundary_ambiguous",
            pd.Series(dtype=bool),
        ).sum()
    )
    summary["featuregraph_invalidated_complete_objects"] = int(
        featuregraph.get(
            "plateau_invalidated_complete",
            pd.Series(dtype=bool),
        ).sum()
    )
    summary["baseline_partial_objects"] = int(
        (~baseline["is_complete"]).sum()
    )
    return {
        "summary": summary,
        "matched": attach_source_columns(matched, window, construction),
        "featuregraph_only": attach_source_columns(
            featuregraph_only,
            window,
            construction,
        ),
        "baseline_only": attach_source_columns(
            baseline_only,
            window,
            construction,
        ),
    }


def combine_tables(
    results: list[dict[str, pd.DataFrame | pd.Series]],
    key: str,
) -> pd.DataFrame:
    """Concatenate one table from every window with stable empty handling."""
    tables = [result[key] for result in results]
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()


def cohort_summary(
    subject_summary: pd.DataFrame,
    matched: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate comparator agreement for each frozen construction."""
    rows: list[dict[str, object]] = []
    for construction, subjects in subject_summary.groupby(
        "construction",
        sort=False,
    ):
        pairs = matched[matched["construction"] == construction]
        rows.append(
            {
                "construction": construction,
                "subjects": len(subjects),
                "featuregraph_complete_objects": int(
                    subjects["featuregraph_complete_objects"].sum()
                ),
                "baseline_complete_objects": int(
                    subjects["llm_complete_objects"].sum()
                ),
                "matched_objects": int(subjects["matched_objects"].sum()),
                "featuregraph_only_objects": int(
                    subjects["featuregraph_only_objects"].sum()
                ),
                "baseline_only_objects": int(
                    subjects["llm_only_objects"].sum()
                ),
                "median_subject_featuregraph_matched_fraction": subjects[
                    "featuregraph_matched_fraction"
                ].median(),
                "median_subject_baseline_matched_fraction": subjects[
                    "llm_matched_fraction"
                ].median(),
                "median_absolute_peak_error_samples": pairs[
                    "delta_peak_index"
                ].abs().median(),
                "p90_absolute_peak_error_samples": pairs[
                    "delta_peak_index"
                ].abs().quantile(0.9),
                "median_absolute_period_error_seconds": pairs[
                    "delta_period_seconds"
                ].abs().median(),
                "median_absolute_full_excursion_error": pairs[
                    "delta_full_excursion"
                ].abs().median(),
                "median_absolute_temporal_symmetry_error": pairs[
                    "delta_temporal_symmetry"
                ].abs().median(),
                "featuregraph_detected_peaks": int(
                    subjects["featuregraph_detected_peaks"].sum()
                ),
                "featuregraph_ambiguous_objects": int(
                    subjects["featuregraph_ambiguous_objects"].sum()
                ),
                "featuregraph_invalidated_complete_objects": int(
                    subjects[
                        "featuregraph_invalidated_complete_objects"
                    ].sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def confirmation_decision(
    subject_summary: pd.DataFrame,
    aggregate: pd.DataFrame,
) -> dict[str, Any]:
    """Evaluate only the four prospectively declared directional criteria."""
    indexed = aggregate.set_index("construction")
    leading = indexed.loc["envelope"]
    plateau = indexed.loc["envelope_plateau"]
    per_subject = subject_summary.pivot(
        index="source_subject",
        columns="construction",
        values="featuregraph_detected_peaks",
    )
    criteria = {
        "peak_count_preserved_every_window": bool(
            per_subject["envelope"].eq(
                per_subject["envelope_plateau"]
            ).all()
        ),
        "matched_objects_not_decreased": bool(
            plateau["matched_objects"] >= leading["matched_objects"]
        ),
        "baseline_only_objects_not_increased": bool(
            plateau["baseline_only_objects"]
            <= leading["baseline_only_objects"]
        ),
        "median_absolute_peak_error_lower": bool(
            plateau["median_absolute_peak_error_samples"]
            < leading["median_absolute_peak_error_samples"]
        ),
    }
    return {
        "criteria": criteria,
        "passed_all_declared_criteria": all(criteria.values()),
    }


def git_revision() -> str:
    """Return the exact repository revision used for the run."""
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of a local protocol or script."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(arguments: argparse.Namespace) -> None:
    """Discover, execute, and save the prospective confirmation."""
    output_directory = arguments.output_directory
    output_directory.mkdir(parents=True, exist_ok=True)
    client = CachedHttpClient(arguments.cache_directory)
    selected, selection_audit, excluded = discover_cohort(
        client,
        target_subjects=arguments.target_subjects,
        jobs=arguments.jobs,
    )

    selection_audit.to_csv(
        output_directory / "selection_audit.csv",
        index=False,
    )
    pd.DataFrame({"subject": excluded}).to_csv(
        output_directory / "curated_bidmc_subjects_excluded.csv",
        index=False,
    )
    selection_manifest = pd.DataFrame(
        [
            {
                "selection_rank": rank,
                "source_subject": window.segment.subject,
                "source_record": window.segment.record_name,
                "header_file": window.segment.header_file,
                "data_file": window.segment.data_file,
                "sampling_rate": window.segment.sampling_rate,
                "source_segment_samples": window.segment.sample_count,
                "window_start_sample": 0,
                "window_samples": WINDOW_SAMPLES,
                "resp_channel_index": window.segment.resp_index,
                "sample_format": window.segment.sample_format,
                "raw_window_sha256": window.raw_sha256,
            }
            for rank, window in enumerate(selected, start=1)
        ]
    )
    selection_manifest.to_csv(
        output_directory / "selection_manifest.csv",
        index=False,
    )

    results: list[dict[str, pd.DataFrame | pd.Series]] = []
    for rank, window in enumerate(selected, start=1):
        for construction in ("envelope", "envelope_plateau"):
            print(
                f"running={rank}/{len(selected)} "
                f"subject={window.segment.subject} "
                f"construction={construction}",
                flush=True,
            )
            results.append(compare_window(window, construction))

    subject_summary = pd.DataFrame([result["summary"] for result in results])
    matched = combine_tables(results, "matched")
    featuregraph_only = combine_tables(results, "featuregraph_only")
    baseline_only = combine_tables(results, "baseline_only")
    aggregate = cohort_summary(subject_summary, matched)
    decision = confirmation_decision(subject_summary, aggregate)

    subject_summary.to_csv(
        output_directory / "subject_summary.csv",
        index=False,
    )
    matched.to_csv(output_directory / "matched_objects.csv", index=False)
    featuregraph_only.to_csv(
        output_directory / "featuregraph_only_objects.csv",
        index=False,
    )
    baseline_only.to_csv(
        output_directory / "baseline_only_objects.csv",
        index=False,
    )
    aggregate.to_csv(output_directory / "cohort_summary.csv", index=False)

    protocol = Path(__file__).with_name("PROTOCOL.md")
    metadata = {
        **decision,
        "git_revision": git_revision(),
        "script_sha256": file_sha256(Path(__file__)),
        "protocol_sha256": file_sha256(protocol),
        "source_base_url": SOURCE_BASE_URL,
        "target_subjects": arguments.target_subjects,
        "selected_subjects": selection_manifest[
            "source_subject"
        ].tolist(),
    }
    (output_directory / "confirmation_decision.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    print(aggregate.to_string(index=False))
    print(json.dumps(metadata, indent=2))


def parse_arguments() -> argparse.Namespace:
    """Parse command-line options without exposing analytical parameters."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target-subjects",
        type=int,
        default=TARGET_SUBJECTS,
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=4,
        help="Concurrent metadata downloads; does not change selection order.",
    )
    parser.add_argument(
        "--cache-directory",
        type=Path,
        default=Path("data/mimic2_confirmation_cache"),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("results/mimic2_envelope_confirmation"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_arguments())
