from abc import ABC, abstractmethod
from collections.abc import Sequence

import pandas as pd

Group = str | Sequence[str] | None
Signals = str | Sequence[str]
Time = str | None


class Behavior(ABC):
    """
    Base class for constructing behavioral objects from observations.
    """

    def __init__(
        self,
        signals: Signals,
        group: Group = None,
        time: Time = None,
    ) -> None:
        if isinstance(signals, str):
            signals = [signals]

        if not signals:
            raise ValueError("At least one signal is required.")

        self.signals = list(signals)
        self.group = group
        self.time = time

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

    def positions(self, df: pd.DataFrame) -> pd.Series:
        """Return zero-based positions within each independent group."""
        if self.group_columns:
            return df.groupby(
                self.group_columns,
                sort=False,
            ).cumcount()

        return pd.Series(range(len(df)), index=df.index)

    def numeric_time(self, df: pd.DataFrame) -> pd.Series | None:
        """Return configured time as numeric values, in seconds for datetimes."""
        if self.time is None:
            return None

        values = df[self.time]
        if isinstance(values.dtype, pd.DatetimeTZDtype):
            return values.astype("int64") / 1_000_000_000
        if pd.api.types.is_datetime64_any_dtype(values):
            return values.astype("int64") / 1_000_000_000
        if pd.api.types.is_numeric_dtype(values):
            return values.astype(float)

        raise TypeError(
            "The time column must contain numeric or datetime values."
        )

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
            *([self.time] if self.time is not None else []),
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

        if not df.index.is_unique:
            raise ValueError(
                "The DataFrame index must be unique so source boundaries "
                "remain unambiguous."
            )

        if self.time is not None:
            numeric_time = self.numeric_time(df)
            assert numeric_time is not None

            if numeric_time.isna().any():
                raise ValueError("The time column cannot contain missing values.")

            if self.group_columns:
                differences = numeric_time.groupby(
                    [df[column] for column in self.group_columns],
                    sort=False,
                ).diff()
            else:
                differences = numeric_time.diff()

            if differences.dropna().le(0).any():
                raise ValueError(
                    "Time values must be strictly increasing within each group."
                )

