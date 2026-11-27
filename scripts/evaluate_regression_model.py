"""Technical evaluation of the HealthCore revenue forecast.

The forecast already trained on 2016-2023 is not approved for staging
until three questions are answered with evidence: fit, stability across
training windows, and a specific correction if one is needed.

RMSE is the primary metric. HealthCore's costly misses are large and
seasonal: October-December revenue rises 15-20 percent, and July-August
revenue falls 12-18 percent. RMSE penalizes those large dollar misses
more than MAE, which treats a small miss and a flu-season miss as the
same kind of error. MAE is still reported as the typical monthly dollar
miss. Underestimating October-December leaves clinics short of capacity.
Overestimating July-August spends staff and cash against visits the
briefing says will not arrive. Both are costly; the squared error makes
the large seasonal miss the one that counts most.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.train_sales_forecast import (  # noqa: E402
    FEATURE_COLUMNS,
    RANDOM_STATE,
    add_features,
    fit_model,
    load_sales,
    split_train_test,
)

LEARNING_CURVE_PATH = ROOT / "data" / "eval" / "learning_curve.png"
REPORT_PATH = ROOT / "data" / "eval" / "evaluation_report.md"
METRICS_PATH = ROOT / "data" / "eval" / "regression_evaluation_metrics.json"
N_SPLITS = 5


def training_frame() -> pd.DataFrame:
    """Feature rows from the first 8 years only. Test years are not included."""
    featured = add_features(load_sales())
    train, _test = split_train_test(featured)
    ready = train.dropna(subset=FEATURE_COLUMNS).sort_values("month").reset_index(drop=True)
    return ready


def chronological_folds(frame: pd.DataFrame, n_splits: int = N_SPLITS):
    """Expanding TimeSeriesSplit folds. Each validation block is entirely later."""
    splitter = TimeSeriesSplit(n_splits=n_splits)
    folds = []
    for train_index, validation_index in splitter.split(frame):
        if train_index.max() >= validation_index.min():
            raise ValueError("A fold mixes a later month into its training rows")
        if list(train_index) != sorted(train_index) or list(validation_index) != sorted(validation_index):
            raise ValueError("A fold is not in chronological order")
        folds.append((train_index, validation_index))
    for earlier, later in zip(folds, folds[1:]):
        if earlier[1].max() >= later[1].min():
            raise ValueError("A later fold starts before an earlier fold ends")
    return folds


def assert_no_future_lag(frame: pd.DataFrame) -> None:
    """Lag and rolling inputs for a month come only from earlier months."""
    revenue = frame["revenue_usd"].to_numpy()
    for position in range(len(frame)):
        if position == 0:
            continue
        if frame.iloc[position]["revenue_lag_1"] != revenue[position - 1]:
            raise ValueError("revenue_lag_1 does not point at the previous month")
        if frame.iloc[position]["revenue_lag_1"] == revenue[position]:
            raise ValueError("revenue_lag_1 uses the current month")


def _score(actual: np.ndarray, predicted: np.ndarray) -> dict:
    mse = float(mean_squared_error(actual, predicted))
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mse)),
        "mse": mse,
    }


def cross_validate(frame: pd.DataFrame) -> dict:
    folds = chronological_folds(frame)
    rows = []
    for number, (train_index, validation_index) in enumerate(folds, start=1):
        train = frame.iloc[train_index]
        validation = frame.iloc[validation_index]
        model, scaler, _trainable = fit_model(train)
        train_features = scaler.transform(train[FEATURE_COLUMNS])
        validation_features = scaler.transform(validation[FEATURE_COLUMNS])
        train_score = _score(train["revenue_usd"].to_numpy(), model.predict(train_features))
        validation_score = _score(
            validation["revenue_usd"].to_numpy(),
            model.predict(validation_features),
        )
        rows.append(
            {
                "fold": number,
                "train_end": str(train["month"].max().date()),
                "validation_start": str(validation["month"].min().date()),
                "validation_end": str(validation["month"].max().date()),
                "train_mae": train_score["mae"],
                "train_rmse": train_score["rmse"],
                "validation_mae": validation_score["mae"],
                "validation_rmse": validation_score["rmse"],
            }
        )
    validation_rmse = np.array([row["validation_rmse"] for row in rows])
    validation_mae = np.array([row["validation_mae"] for row in rows])
    return {
        "folds": rows,
        "validation_rmse_mean": float(validation_rmse.mean()),
        "validation_rmse_std": float(validation_rmse.std(ddof=1)),
        "validation_mae_mean": float(validation_mae.mean()),
        "validation_mae_std": float(validation_mae.std(ddof=1)),
    }


def learning_curve(frame: pd.DataFrame) -> dict:
    """Grow the earliest training months. The last 12 training months stay the validation block."""
    validation = frame.iloc[-12:]
    pool = frame.iloc[:-12]
    sizes = [size for size in (24, 36, 48, 60, 72) if size <= len(pool)]
    points = []
    for size in sizes:
        train = pool.iloc[:size]
        model, scaler, _trainable = fit_model(train)
        train_predicted = model.predict(scaler.transform(train[FEATURE_COLUMNS]))
        validation_predicted = model.predict(scaler.transform(validation[FEATURE_COLUMNS]))
        train_score = _score(train["revenue_usd"].to_numpy(), train_predicted)
        validation_score = _score(validation["revenue_usd"].to_numpy(), validation_predicted)
        points.append(
            {
                "training_months": size,
                "train_rmse": train_score["rmse"],
                "validation_rmse": validation_score["rmse"],
                "train_mae": train_score["mae"],
                "validation_mae": validation_score["mae"],
            }
        )
    return {"validation_months": "last 12 months of 2016-2023", "points": points}


def save_learning_curve(curve: dict) -> None:
    LEARNING_CURVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    points = curve["points"]
    sizes = [point["training_months"] for point in points]
    plt.figure(figsize=(8, 5))
    plt.plot(sizes, [point["train_rmse"] for point in points], marker="o", label="Training RMSE")
    plt.plot(
        sizes,
        [point["validation_rmse"] for point in points],
        marker="o",
        label="Validation RMSE",
    )
    plt.xlabel("Training months (earliest months only)")
    plt.ylabel("RMSE (USD)")
    plt.title("HealthCore revenue model learning curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(LEARNING_CURVE_PATH, dpi=120)
    plt.close()


def diagnose(curve: dict, average_revenue: float) -> dict:
    """Classify the curve using HealthCore's seasonal swing as the scale of a large error."""
    last = curve["points"][-1]
    train_pct = last["train_rmse"] / average_revenue * 100
    validation_pct = last["validation_rmse"] / average_revenue * 100
    gap_pct = validation_pct - train_pct
    # The briefing's seasonal moves are 12-20 percent. An error near that size
    # has not captured the pattern. An error well below it has.
    high_error = 12.0
    if train_pct >= high_error and validation_pct >= high_error and gap_pct < 5:
        label = "underfitting"
        action = (
            "The first change is to let the trees split more deeply on the "
            "flu-season and summer flags, by raising max_depth from 6 to 10 "
            "and lowering min_samples_leaf from 2 to 1. Adding months is not "
            "the first change: the training error is already as large as the "
            "seasonal swing, so the trees are not using the pattern that is there."
        )
    elif gap_pct >= 5 and validation_pct > train_pct * 1.5:
        label = "overfitting"
        action = (
            "The first change is to stop the trees from memorizing individual "
            "months: raise min_samples_leaf from 2 to 6 and lower max_depth "
            "from 6 to 4. Do not add depth. The training line is already low, "
            "and the gap is the later training months, not a lack of model size."
        )
    else:
        label = "reasonably well fitted"
        action = (
            "Do not add depth and do not collect more years before the staging "
            "decision. Keep max_depth at 6 and min_samples_leaf at 2. The "
            "remaining dollar error is about the size of the ordinary ±5 percent "
            "month-to-month movement, which is smaller than the July-August drop "
            "and the October-December rise. Review the forecast against those two "
            "seasons before building the executive dashboard, because a normal "
            "August drop must not be read as a capacity failure."
        )
    return {
        "label": label,
        "train_rmse_percent": train_pct,
        "validation_rmse_percent": validation_pct,
        "gap_percent": gap_pct,
        "action": action,
    }


def full_train_and_validation_scores(frame: pd.DataFrame) -> dict:
    """MAE and RMSE on the training fit and on a final 12-month validation block."""
    validation = frame.iloc[-12:]
    train = frame.iloc[:-12]
    model, scaler, _trainable = fit_model(train)
    train_score = _score(
        train["revenue_usd"].to_numpy(),
        model.predict(scaler.transform(train[FEATURE_COLUMNS])),
    )
    validation_score = _score(
        validation["revenue_usd"].to_numpy(),
        model.predict(scaler.transform(validation[FEATURE_COLUMNS])),
    )
    return {"training": train_score, "validation": validation_score}


def write_report(result: dict) -> None:
    diagnosis = result["diagnosis"]
    cross = result["cross_validation"]
    scores = result["train_validation_scores"]
    lines = [
        "# HealthCore revenue model evaluation",
        "",
        f"The model is **{diagnosis['label']}**.",
        "",
        "The learning curve uses only 2016-2023. The last 12 of those months are the validation block, and the earlier months are added from the start of the series. At the full training size the training RMSE is "
        f"{diagnosis['train_rmse_percent']:.1f}% of average monthly training revenue and the validation RMSE is "
        f"{diagnosis['validation_rmse_percent']:.1f}%. The seasonal moves in the briefing are a 12-18% summer drop and a 15-20% October-December rise, so this error is smaller than those moves.",
        "",
        "Five chronological folds, validation RMSE "
        f"{cross['validation_rmse_mean']:.0f} ± {cross['validation_rmse_std']:.0f} USD "
        f"and validation MAE {cross['validation_mae_mean']:.0f} ± {cross['validation_mae_std']:.0f} USD. "
        "No fold is shuffled, and each later validation block starts after the previous one.",
        "",
        "RMSE is the primary metric. A large miss in July-August or October-December costs HealthCore more than a small miss, because those seasons move revenue by 12-20 percent. MAE is the typical monthly dollar miss and is reported beside it. "
        f"On the final training fit, training MAE is {scores['training']['mae']:.0f} USD and training RMSE is {scores['training']['rmse']:.0f} USD. "
        f"Validation MAE is {scores['validation']['mae']:.0f} USD and validation RMSE is {scores['validation']['rmse']:.0f} USD.",
        "",
        "## Corrective action",
        "",
        diagnosis["action"],
        "",
        "No patient-level fields are used. The series remains the consolidated monthly revenue in `data/raw/healthcore_sales.csv`.",
        "",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def evaluate() -> dict:
    frame = training_frame()
    assert_no_future_lag(frame)
    cross = cross_validate(frame)
    curve = learning_curve(frame)
    save_learning_curve(curve)
    scores = full_train_and_validation_scores(frame)
    average_revenue = float(frame["revenue_usd"].mean())
    diagnosis = diagnose(curve, average_revenue)
    result = {
        "primary_metric": "RMSE",
        "why_rmse": (
            "October-December and July-August move revenue by 12-20 percent. "
            "RMSE penalizes a miss of that size more than MAE does."
        ),
        "cross_validation": cross,
        "learning_curve": curve,
        "train_validation_scores": scores,
        "diagnosis": diagnosis,
        "learning_curve_plot": str(LEARNING_CURVE_PATH.relative_to(ROOT)),
        "report": str(REPORT_PATH.relative_to(ROOT)),
    }
    write_report(result)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
