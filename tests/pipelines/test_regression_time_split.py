"""Time-series folds stay in chronological order and do not look ahead."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_regression_model import (
    assert_no_future_lag,
    chronological_folds,
    training_frame,
)


def test_folds_keep_chronological_order() -> None:
    frame = training_frame()
    folds = chronological_folds(frame, n_splits=5)
    assert len(folds) == 5
    previous_validation_end = -1
    for train_index, validation_index in folds:
        assert train_index.max() < validation_index.min()
        assert list(validation_index) == sorted(validation_index)
        assert validation_index.min() > previous_validation_end
        previous_validation_end = int(validation_index.max())
        train_months = frame.iloc[train_index]["month"]
        validation_months = frame.iloc[validation_index]["month"]
        assert train_months.max() < validation_months.min()


def test_lag_features_do_not_read_a_future_month() -> None:
    frame = training_frame()
    assert_no_future_lag(frame)
    folds = chronological_folds(frame, n_splits=5)
    for _train_index, validation_index in folds:
        for position in validation_index:
            current = frame.iloc[position]
            previous = frame.iloc[position - 1]
            assert current["month"] > previous["month"]
            assert current["revenue_lag_1"] == previous["revenue_usd"]
