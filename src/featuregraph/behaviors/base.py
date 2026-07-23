from abc import ABC, abstractmethod
from collections.abc import Sequence

import pandas as pd


Group = str | Sequence[str] | None
Signals = str | Sequence[str]


class Behavior(ABC):
    """
    Base class for constructing behavioral objects from observations.
    """

    def __init__(
        self,
        signals: Signals,
        group: Group = None,
    ) -> None:
        if isinstance(signals, str):
            signals = [signals]

        if not signals:
            raise ValueError("At least one signal is required.")

        self.signals = list(signals)
        self.group = group

    @property
    def group_columns(self) -> list[str]:
        """Return the observation grouping columns as a list."""
        if self.group is None:
            return []

        if isinstance(self.group, str):
            return [self.group]

        return list(self.group)

    def object_group(
        self,
        signal: str,
        id_suffix: str,
    ) -> list[str]:
        """
        Return grouping columns that uniquely identify one object.
        """
        return [
            *self.group_columns,
            f"{signal}_{id_suffix}",
        ]

    def fit_transform(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Run the behavioral-object construction pipeline.
        """
        self.validate(df)

        result = df.copy()
        result = self.add_signal(result)
        result = self.add_primitives(result)
        result = self.add_ids(result)
        result = self.add_features(result)

        return result

    def add_signal(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Optionally derive the signal represented by the behavior.

        Most behaviors operate directly on an observed signal, so the
        default implementation returns the DataFrame unchanged.
        """
        return df

    @abstractmethod
    def add_primitives(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Derive the primitive states, events, or quantities."""
        raise NotImplementedError

    @abstractmethod
    def add_ids(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Assign an identifier to every behavioral object."""
        raise NotImplementedError

    @abstractmethod
    def add_features(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Calculate row-level and object-relative measurements."""
        raise NotImplementedError

    @abstractmethod
    def summarize(
        self,
        df: pd.DataFrame,
        signal: str,
    ) -> pd.DataFrame:
        """Return one row per behavioral object."""
        raise NotImplementedError

    def validate_signal(
        self,
        df: pd.DataFrame,
        signal: str,
    ) -> None:
        if signal not in df.columns:
            raise ValueError(
                f"Signal {signal!r} is not present in the DataFrame."
            )

    def validate(self, df: pd.DataFrame) -> None:
        """Validate required signal and grouping columns."""
        required = [
            *self.signals,
            *self.group_columns,
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Required columns are missing: {missing}"
            )


