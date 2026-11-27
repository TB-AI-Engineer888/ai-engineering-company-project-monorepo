"""Time-series folds stay in chronological order and do not look ahead."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_regression_model import (
    ROLLING_SOURCES,
    assert_no_fold_leak,
    assert_no_future_lag,
    chronological_folds,
    training_frame,
    training_series,
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


def test_lag_and_rolling_features_do_not_read_a_future_fold() -> None:
    series = training_series()
    assert_no_future_lag(series)
    ready = training_frame()
    folds = chronological_folds(ready, n_splits=5)
    assert_no_fold_leak(ready, folds)
    for train_index, validation_index in folds:
        validation_months = set(ready.iloc[validation_index]["month"])
        for position in train_index:
            row = ready.iloc[position]
            assert row["revenue_lag_1"] != row["revenue_usd"]
            assert row["month"] not in validation_months
        for column in ROLLING_SOURCES:
            assert column in ready.columns
