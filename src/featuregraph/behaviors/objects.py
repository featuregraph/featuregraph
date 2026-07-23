from dataclasses import dataclass, field
from typing import Any

import pandas as pd

@dataclass
class BehaviorObjects:
    """
    Constructed behavioral objects and their supporting representation.
    """

    behavior_type: str
    signal: str
    table: pd.DataFrame
    features: pd.DataFrame
    group: tuple[str, ...]
    properties: tuple[str, ...]
    construction: dict[str, Any] = field(
        default_factory=dict
    )
    parent_behavior: str | None = None
    parent_id: str | None = None

    def __len__(self) -> int:
        return len(self.table)

    @property
    def count(self) -> int:
        return len(self.table)

    @property
    def columns(self) -> list[str]:
        return self.table.columns.tolist()

    def to_pandas(self, copy: bool = True) -> pd.DataFrame:
        if copy:
            return self.table.copy()

        return self.table

    def query(self) -> "ObjectQuery":
        return ObjectQuery(self)




OPERATORS = {
    "eq": lambda column, value: column == value,
    "ne": lambda column, value: column != value,
    "gt": lambda column, value: column > value,
    "ge": lambda column, value: column >= value,
    "lt": lambda column, value: column < value,
    "le": lambda column, value: column <= value,
    "in": lambda column, value: column.isin(value),
}


class ObjectQuery:
    """A small query interface for behavioral object tables."""

    def __init__(
        self,
        objects: BehaviorObjects,
        table: pd.DataFrame | None = None,
    ) -> None:
        self.objects = objects

        self._table = (
            objects.table.copy()
            if table is None
            else table
        )

    def where(
        self,
        **conditions: Any,
    ) -> "ObjectQuery":
        mask = pd.Series(
            True,
            index=self._table.index,
        )

        for expression, value in conditions.items():
            column, separator, operator = (
                expression.rpartition("__")
            )

            if not separator:
                column = expression
                operator = "eq"

            if column not in self._table.columns:
                raise KeyError(
                    f"Unknown object property: {column!r}"
                )

            if operator not in OPERATORS:
                raise ValueError(
                    f"Unsupported query operator: {operator!r}"
                )

            mask &= OPERATORS[operator](
                self._table[column],
                value,
            )

        return ObjectQuery(
            self.objects,
            self._table.loc[mask].copy(),
        )

    def select(
        self,
        *columns: str,
    ) -> "ObjectQuery":
        missing = [
            column
            for column in columns
            if column not in self._table.columns
        ]

        if missing:
            raise KeyError(
                f"Unknown object properties: {missing}"
            )

        return ObjectQuery(
            self.objects,
            self._table.loc[:, list(columns)].copy(),
        )

    def order_by(
        self,
        column: str,
        ascending: bool = True,
    ) -> "ObjectQuery":
        if column not in self._table.columns:
            raise KeyError(
                f"Unknown object property: {column!r}"
            )

        table = self._table.sort_values(
            column,
            ascending=ascending,
        )

        return ObjectQuery(
            self.objects,
            table,
        )

    def limit(self, n: int) -> "ObjectQuery":
        if n < 0:
            raise ValueError("n cannot be negative.")

        return ObjectQuery(
            self.objects,
            self._table.head(n).copy(),
        )

    def collect(self) -> pd.DataFrame:
        return self._table.reset_index(drop=True)