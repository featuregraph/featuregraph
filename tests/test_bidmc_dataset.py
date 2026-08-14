import pandas as pd

import featuregraph as fg


def test_bidmc_breaths_is_public_and_forwards_options(monkeypatch) -> None:
    expected = pd.DataFrame(
        {
            "breaths ann1 [signal sample no]": [100],
            "breaths ann2 [signal sample no]": [102],
            "subject": [3],
        }
    )
    calls = []

    def fake_loader(subject, *, refresh=False):
        calls.append((subject, refresh))
        return expected

    monkeypatch.setattr(
        "featuregraph.datasets._bidmc.load_bidmc_breaths",
        fake_loader,
    )

    result = fg.datasets.bidmc_breaths(3, refresh=True)

    assert result is expected
    assert calls == [(3, True)]
