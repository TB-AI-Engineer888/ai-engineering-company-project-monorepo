"""HealthCore monthly revenue forecast.

Random Forest is used instead of XGBoost. Finance and the CEO need a
number they can explain: the forecast is the average of many trees, and
the shaded band is the spread of those trees. The training set is 96
months, which is small enough that a sequential booster is easy to
overfit and harder to explain. The choice is explainability for the
stakeholder, not a claim that one algorithm is always more accurate.

Metrics are computed on the test years only (2024-2025):

- MSE is the average squared dollar error. A small MSE can still hide a
  model that misses the summer drop or the flu-season rise, so it is
  also shown as a percentage of average monthly test revenue.
- PSI compares the training and test distributions. A large PSI means
  the later years do not look like the years the model learned. The
  file has only consolidated rows, so it cannot show a US/UK visit-mix
  shift directly.
- Gini measures whether higher predictions line up with higher actual
  months. It answers the ranking question MSE does not.
- K2 is the coefficient of determination (R2) on the test set: the
  share of test-revenue variance the forecast explains.

Features use only earlier months and the calendar. The target month's
own revenue and visit count are not inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "raw" / "healthcore_sales.csv"
PLOT_PATH = ROOT / "data" / "eval" / "healthcore_sales_forecast.png"
METRICS_PATH = ROOT / "data" / "eval" / "healthcore_sales_forecast_metrics.json"
MODEL_PATH = ROOT / "models" / "healthcore_sales_random_forest.joblib"

RANDOM_STATE = 42
TRAIN_YEARS = 8
TEST_YEARS = 2
FEATURE_COLUMNS = [
    "month_of_year",
    "is_flu_season",
    "is_summer",
    "revenue_lag_1",
    "revenue_lag_12",
    "visits_lag_1",
    "visits_lag_12",
    "avg_revenue_lag_1",
    "revenue_roll_mean_3",
    "revenue_roll_std_3",
    "visits_roll_mean_3",
]


def load_sales(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load the provided consolidated monthly series and reject broken rows."""
    frame = pd.read_csv(path)
    expected = [
        "month",
        "revenue_usd",
        "visits_count",
        "avg_revenue_per_visit_usd",
        "region",
    ]
    if list(frame.columns) != expected:
        raise ValueError(f"Columns must be {expected}, found {list(frame.columns)}")
    frame["month"] = pd.to_datetime(frame["month"])
    frame = frame.sort_values("month").reset_index(drop=True)
    frame = frame.dropna(subset=["revenue_usd", "visits_count", "avg_revenue_per_visit_usd"])
    if (frame["revenue_usd"] <= 0).any():
        raise ValueError("Every revenue_usd value must be positive")
    if not (frame["region"] == "consolidated").all():
        raise ValueError("The model uses the consolidated row only")
    months = pd.Series(frame["month"].dt.to_period("M"))
    expected_months = pd.period_range("2016-01", "2025-12", freq="M")
    if not months.reset_index(drop=True).equals(pd.Series(expected_months)):
        raise ValueError("The series must contain every month from 2016-01 through 2025-12")
    return frame


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add calendar and past-only features. The current row is never an input."""
    featured = frame.copy()
    featured["month_of_year"] = featured["month"].dt.month
    featured["is_flu_season"] = featured["month_of_year"].isin([10, 11, 12]).astype(int)
    featured["is_summer"] = featured["month_of_year"].isin([7, 8]).astype(int)
    featured["revenue_lag_1"] = featured["revenue_usd"].shift(1)
    featured["revenue_lag_12"] = featured["revenue_usd"].shift(12)
    featured["visits_lag_1"] = featured["visits_count"].shift(1)
    featured["visits_lag_12"] = featured["visits_count"].shift(12)
    featured["avg_revenue_lag_1"] = featured["avg_revenue_per_visit_usd"].shift(1)
    past_revenue = featured["revenue_usd"].shift(1)
    past_visits = featured["visits_count"].shift(1)
    featured["revenue_roll_mean_3"] = past_revenue.rolling(3).mean()
    featured["revenue_roll_std_3"] = past_revenue.rolling(3).std()
    featured["visits_roll_mean_3"] = past_visits.rolling(3).mean()
    return featured


def split_train_test(frame: pd.DataFrame, train_years: int = TRAIN_YEARS, test_years: int = TEST_YEARS):
    """First 8 calendar years for training, last 2 for checking. No shared year."""
    years = sorted(frame["month"].dt.year.unique())
    if len(years) != train_years + test_years:
        raise ValueError(f"Expected {train_years + test_years} years, found {years}")
    train_year_set = set(years[:train_years])
    test_year_set = set(years[-test_years:])
    if train_year_set & test_year_set:
        raise ValueError("Training years and test years overlap")
    train = frame[frame["month"].dt.year.isin(train_year_set)].copy()
    test = frame[frame["month"].dt.year.isin(test_year_set)].copy()
    if train["month"].max() >= test["month"].min():
        raise ValueError("Training data includes a test month")
    return train, test


def population_stability_index(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """PSI of the test distribution against the training distribution."""
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    breaks = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    if len(breaks) < 3:
        return 0.0
    expected_counts = np.histogram(expected, bins=breaks)[0].astype(float)
    actual_counts = np.histogram(actual, bins=breaks)[0].astype(float)
    expected_pct = np.clip(expected_counts / expected_counts.sum(), 1e-6, None)
    actual_pct = np.clip(actual_counts / max(actual_counts.sum(), 1.0), 1e-6, None)
    expected_pct = expected_pct / expected_pct.sum()
    actual_pct = actual_pct / actual_pct.sum()
    return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))


def normalized_gini(actual: np.ndarray, predicted: np.ndarray) -> float:
    """How well the ranking of predictions matches the ranking of actual revenue."""

    def _gini(values: np.ndarray, order_by: np.ndarray) -> float:
        order = np.argsort(order_by)
        sorted_values = values[order]
        cumulative = np.cumsum(sorted_values)
        total = cumulative[-1]
        count = len(values)
        if total == 0:
            return 0.0
        return (count + 1 - 2 * np.sum(cumulative) / total) / count

    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    perfect = _gini(actual, actual)
    if perfect == 0:
        return 0.0
    return float(_gini(actual, predicted) / perfect)


def fit_model(train: pd.DataFrame):
    """Scale on the training years only, then fit the forest."""
    trainable = train.dropna(subset=FEATURE_COLUMNS).copy()
    scaler = StandardScaler()
    features = scaler.fit_transform(trainable[FEATURE_COLUMNS])
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    model.fit(features, trainable["revenue_usd"].to_numpy())
    return model, scaler, trainable


def predict_with_band(model: RandomForestRegressor, features: np.ndarray):
    """Mean prediction and the spread across the individual trees."""
    tree_predictions = np.column_stack([tree.predict(features) for tree in model.estimators_])
    mean = tree_predictions.mean(axis=1)
    low = np.percentile(tree_predictions, 10, axis=1)
    high = np.percentile(tree_predictions, 90, axis=1)
    return mean, low, high


def evaluate(model, scaler: StandardScaler, train: pd.DataFrame, test: pd.DataFrame) -> dict:
    test_ready = test.dropna(subset=FEATURE_COLUMNS).copy()
    features = scaler.transform(test_ready[FEATURE_COLUMNS])
    predicted, low, high = predict_with_band(model, features)
    actual = test_ready["revenue_usd"].to_numpy()
    mse = float(mean_squared_error(actual, predicted))
    average_revenue = float(actual.mean())
    return {
        "mse": mse,
        "rmse_usd": float(np.sqrt(mse)),
        "rmse_percent_of_average_monthly_revenue": float(np.sqrt(mse) / average_revenue * 100),
        "average_test_monthly_revenue_usd": average_revenue,
        "psi_visits_count": population_stability_index(
            train["visits_count"].to_numpy(),
            test["visits_count"].to_numpy(),
        ),
        "psi_revenue_usd": population_stability_index(train["revenue_usd"].to_numpy(), actual),
        "gini": normalized_gini(actual, predicted),
        "k2_score": float(r2_score(actual, predicted)),
        "months": test_ready["month"].dt.strftime("%Y-%m-%d").tolist(),
        "actual": actual.tolist(),
        "predicted": predicted.tolist(),
        "band_low": low.tolist(),
        "band_high": high.tolist(),
    }


def save_plot(metrics: dict, path: Path = PLOT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    months = pd.to_datetime(metrics["months"])
    plt.figure(figsize=(10, 5))
    plt.plot(months, metrics["actual"], label="Actual revenue", color="#0f3d5e")
    plt.plot(months, metrics["predicted"], label="Predicted revenue", color="#d97706")
    plt.fill_between(
        months,
        metrics["band_low"],
        metrics["band_high"],
        color="#d97706",
        alpha=0.2,
        label="Variability across trees (10th-90th)",
    )
    plt.title("HealthCore consolidated revenue, test years 2024-2025")
    plt.ylabel("Revenue (USD)")
    plt.xlabel("Month")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=120)
    plt.close()


def train_and_report() -> dict:
    sales = add_features(load_sales())
    train, test = split_train_test(sales)
    model, scaler, trainable = fit_model(train)
    metrics = evaluate(model, scaler, trainable, test)
    save_plot(metrics)
    report = {
        "algorithm": "RandomForestRegressor",
        "random_state": RANDOM_STATE,
        "why": (
            "Random Forest is the average of many trees, so Finance can see "
            "both the forecast and how widely the trees disagree. XGBoost can "
            "be more accurate but is harder to explain and easier to overfit "
            "on 96 monthly rows."
        ),
        "train_months": int(trainable.shape[0]),
        "test_months": int(len(metrics["actual"])),
        "mse": metrics["mse"],
        "rmse_usd": metrics["rmse_usd"],
        "rmse_percent_of_average_monthly_revenue": metrics[
            "rmse_percent_of_average_monthly_revenue"
        ],
        "psi_visits_count": metrics["psi_visits_count"],
        "psi_revenue_usd": metrics["psi_revenue_usd"],
        "gini": metrics["gini"],
        "k2_score": metrics["k2_score"],
        "plot": str(PLOT_PATH.relative_to(ROOT)),
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    import joblib

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "scaler": scaler, "features": FEATURE_COLUMNS}, MODEL_PATH)
    return report


if __name__ == "__main__":
    print(json.dumps(train_and_report(), indent=2))
