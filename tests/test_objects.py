import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from featuregraph.behaviors.objects import BehaviorObjects


@pytest.fixture
def behavior_objects() -> BehaviorObjects:
    table = pd.DataFrame(
        {
            "object_id": [1, 2, 3],
            "duration": [5, 10, 15],
            "amplitude": [0.5, 1.5, 1.0],
        }
    )
    features = pd.DataFrame({"signal": [0.0, 1.0, 0.0]})

    return BehaviorObjects(
        behavior_type="oscillation",
        signal="signal",
        table=table,
        features=features,
        group=(),
        properties=tuple(table.columns),
        construction={"diff_lag": 1},
    )


def test_behavior_objects_exposes_table_metadata(
    behavior_objects: BehaviorObjects,
) -> None:
    assert len(behavior_objects) == 3
    assert behavior_objects.count == 3
    assert behavior_objects.columns == [
        "object_id",
        "duration",
        "amplitude",
    ]
    assert behavior_objects.behavior_type == "oscillation"
    assert behavior_objects.signal == "signal"


def test_to_pandas_returns_a_copy_by_default(
    behavior_objects: BehaviorObjects,
) -> None:
    result = behavior_objects.to_pandas()
    result.loc[0, "duration"] = 100

    assert behavior_objects.table.loc[0, "duration"] == 5
    assert behavior_objects.to_pandas(copy=False) is behavior_objects.table


def test_query_filters_selects_orders_and_limits(
    behavior_objects: BehaviorObjects,
) -> None:
    result = (
        behavior_objects.query()
        .where(duration__ge=10)
        .select("object_id", "amplitude")
        .order_by("amplitude", ascending=False)
        .limit(1)
        .collect()
    )

    expected = pd.DataFrame(
        {
            "object_id": [2],
            "amplitude": [1.5],
        }
    )
    assert_frame_equal(result, expected)


def test_query_supports_equality_and_membership(
    behavior_objects: BehaviorObjects,
) -> None:
    equal = behavior_objects.query().where(object_id=2).collect()
    included = (
        behavior_objects.query()
        .where(object_id__in=[1, 3])
        .collect()
    )

    assert equal["object_id"].tolist() == [2]
    assert included["object_id"].tolist() == [1, 3]


@pytest.mark.parametrize(
    ("operation", "error", "message"),
    [
        (lambda query: query.where(missing=1), KeyError, "Unknown object property"),
        (lambda query: query.where(duration__bad=1), ValueError, "Unsupported"),
        (lambda query: query.select("missing"), KeyError, "Unknown object properties"),
        (lambda query: query.order_by("missing"), KeyError, "Unknown object property"),
        (lambda query: query.limit(-1), ValueError, "cannot be negative"),
    ],
)
def test_query_rejects_invalid_operations(
    behavior_objects: BehaviorObjects,
    operation,
    error: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error, match=message):
        operation(behavior_objects.query())
