"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train
"""
import argparse
import json

import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import METRICS, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)



class RatioTarget(BaseEstimator, RegressorMixin):
    """Exercise 4 only, off by default (`--target ratio`).

    Fit the wrapped model on cnt / cnt_roll_7 (today relative to the past
    week) and multiply its prediction back by cnt_roll_7. The ratio sits
    near 1 in both 2011 and 2012, so a tree no longer has to predict counts
    above anything it saw in training. cnt_roll_7 is shifted before it is
    rolled, so it is known at prediction time.
    """

    def __init__(self, model, scale_col: str = "cnt_roll_7"):
        self.model = model
        self.scale_col = scale_col

    def fit(self, X, y):
        self.model_ = clone(self.model).fit(X, y / X[self.scale_col])
        return self

    def predict(self, X):
        return self.model_.predict(X) * X[self.scale_col].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def fit_and_score(target: str = "raw", show_test: bool = True) -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    models = dict(MODELS)
    if target == "ratio":
        # Baselines stay as they are; only the two learned models change.
        models["ridge"] = RatioTarget(MODELS["ridge"])
        models["hgb"] = RatioTarget(MODELS["hgb"])
    results["target"] = target
    splits = [("valid", valid)] + ([("test", test)] if show_test else [])
    for name, model in models.items():
        model.fit(train[cols], train[TARGET])
        results[name] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in splits
        }
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["raw", "ratio"], default="raw",
                    help="ratio: Exercise 4 transform. Never written to metrics.json.")
    ap.add_argument("--show-test", action="store_true",
                    help="with --target ratio, also score the test set (do this once).")
    args = ap.parse_args()

    if args.target == "raw":
        res = fit_and_score()
        res.pop("target")
        METRICS.parent.mkdir(parents=True, exist_ok=True)
        METRICS.write_text(json.dumps(res, indent=2))
    else:
        res = fit_and_score("ratio", show_test=args.show_test)
        out = METRICS.with_name("exercise4_ratio.json")
        out.write_text(json.dumps(res, indent=2))
        print(f"(Exercise 4; reports/metrics.json untouched) -> {out.name}")
    print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
