"""The sales forecast split is the first 8 years, then the last 2, with no leakage."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.train_sales_forecast import (
    FEATURE_COLUMNS,
    add_features,
    load_sales,
    split_train_test,
)


def test_split_is_first_eight_years_and_last_two_years() -> None:
    sales = load_sales()
    train, test = split_train_test(add_features(sales))

    assert train["month"].dt.year.min() == 2016
    assert train["month"].dt.year.max() == 2023
    assert test["month"].dt.year.min() == 2024
    assert test["month"].dt.year.max() == 2025
    assert len(train) == 96
    assert len(test) == 24
    assert set(train["month"]).isdisjoint(set(test["month"]))
    assert train["month"].max() < test["month"].min()


def test_features_do_not_use_the_current_months_revenue() -> None:
    featured = add_features(load_sales())
    # January 2017 is the first row with a full year of history.
    row = featured.loc[featured["month"] == "2017-01-01"].iloc[0]
    prior = featured.loc[featured["month"] == "2016-12-01"].iloc[0]
    year_ago = featured.loc[featured["month"] == "2016-01-01"].iloc[0]

    assert row["revenue_lag_1"] == prior["revenue_usd"]
    assert row["revenue_lag_12"] == year_ago["revenue_usd"]
    assert row["revenue_lag_1"] != row["revenue_usd"]
    assert "revenue_usd" not in FEATURE_COLUMNS
    assert "visits_count" not in FEATURE_COLUMNS
