"""Record SHA-256 fingerprints of BIDMC source files.

Run this once from an environment that can reach PhysioNet. It downloads the
requested subjects, hashes what actually arrived, and writes the result to
``src/featuregraph/datasets/bidmc_manifest.json``. From then on a cached or
re-downloaded file that does not match is refused rather than used.

    python -m scripts.record_bidmc_manifest                 # subject 1
    python -m scripts.record_bidmc_manifest --subjects 1-53 # the full cohort
    python -m scripts.record_bidmc_manifest --subjects 1 --kinds Signals Numerics

Recording a fingerprint is an assertion that the bytes you fetched are the ones
you intend every future run to use. Re-run with ``--refresh`` only when you mean
to adopt a revised upstream file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from featuregraph.studies.fingerprint import file_sha256
from featuregraph.utils._bidmc import (
    BIDMC_MANIFEST_PATH,
    BIDMC_VERSION,
    bidmc_filename,
    download_bidmc_file,
)

KINDS = ("Signals", "Numerics", "Breaths")


def parse_subjects(text: str) -> list[int]:
    """Accept ``3``, ``1-53``, or ``1,4,9``."""
    subjects: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            start, _, end = part.partition("-")
            subjects.extend(range(int(start), int(end) + 1))
        elif part:
            subjects.append(int(part))
    out = sorted(set(subjects))
    if not out or out[0] < 1 or out[-1] > 53:
        raise SystemExit("subjects must lie between 1 and 53")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subjects", default="1", help="e.g. 1, 1-53, or 1,4,9")
    parser.add_argument("--kinds", nargs="*", default=["Signals"], choices=KINDS)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-download and adopt the current upstream bytes.",
    )
    parser.add_argument("--out", default=str(BIDMC_MANIFEST_PATH))
    args = parser.parse_args()

    out_path = Path(args.out)
    manifest = (
        json.loads(out_path.read_text(encoding="utf-8")) if out_path.is_file() else {}
    )
    manifest.setdefault("dataset", "bidmc")
    manifest.setdefault("version", BIDMC_VERSION)
    manifest.setdefault("algorithm", "sha256")
    files: dict[str, str] = dict(manifest.get("files", {}))

    changed = 0
    for subject in parse_subjects(args.subjects):
        for kind in args.kinds:
            filename = bidmc_filename(subject, kind)
            # refresh bypasses verification against the current manifest, which
            # is what makes adopting a revised upstream file a deliberate act.
            path = download_bidmc_file(subject, kind, refresh=args.refresh)
            digest = file_sha256(path)
            previous = files.get(filename)
            if previous == digest:
                print(f"  unchanged  {filename}  {digest[:16]}...")
                continue
            marker = "recorded  " if previous is None else "UPDATED   "
            print(f"  {marker} {filename}  {digest[:16]}...")
            if previous is not None:
                print(f"             was {previous[:16]}...")
            files[filename] = digest
            changed += 1

    manifest["files"] = dict(sorted(files.items()))
    out_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"\n{len(files)} file(s) pinned, {changed} changed -> {out_path}")
    if changed:
        print("Review the diff before committing: each line is a claim about which "
              "bytes every future run must use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
