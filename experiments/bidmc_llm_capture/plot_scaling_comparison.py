"""Plot per-subject object counts for both FeatureGraph constructions."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).parents[2]
RESULTS = Path(__file__).parent / "results"
OUTPUT = (
    ROOT
    / "artifacts"
    / "paper"
    / "bidmc_llm_preservation_study"
    / "subject_object_counts.png"
)


def main() -> None:
    absolute = pd.read_csv(
        RESULTS / "multi_subject" / "subject_summary.csv"
    )
    mad = pd.read_csv(
        RESULTS / "mad_multi_subject" / "subject_summary.csv"
    )
    comparison = absolute[
        [
            "subject",
            "featuregraph_complete_objects",
            "llm_complete_objects",
        ]
    ].rename(
        columns={
            "featuregraph_complete_objects": "absolute",
            "llm_complete_objects": "baseline",
        }
    )
    comparison = comparison.merge(
        mad[["subject", "featuregraph_complete_objects"]].rename(
            columns={"featuregraph_complete_objects": "mad"}
        ),
        on="subject",
        how="left",
    )

    figure, axis = plt.subplots(figsize=(11, 5.5))
    axis.plot(
        comparison["subject"],
        comparison["baseline"],
        label="Frozen LLM-selected baseline",
        linewidth=2,
    )
    axis.plot(
        comparison["subject"],
        comparison["absolute"],
        label="FeatureGraph absolute threshold",
        linewidth=1.8,
    )
    axis.plot(
        comparison["subject"],
        comparison["mad"],
        label="FeatureGraph MAD normalized",
        linewidth=1.8,
    )
    axis.scatter(
        [35, 39],
        [0, 0],
        marker="x",
        color="black",
        label="MAD undefined",
        zorder=5,
    )
    axis.set(
        xlabel="BIDMC subject",
        ylabel="Complete candidate objects",
        title="MAD normalization changes mixed transfer errors into over-segmentation",
        xlim=(1, 53),
        ylim=(0, None),
    )
    axis.grid(alpha=0.25)
    axis.legend(frameon=False, ncols=2)
    figure.tight_layout()
    figure.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    plt.close(figure)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
