# Seeded faults (Exercise 2)

Each fault was seeded by the local agent (qwen3.5:9b via Ollama, 64k context) in
Claude Code, with the PostToolUse hook in `.claude/settings.json` active. The red
test output is `make test` (`python -m pytest tests/ -q`) run by hand right after
the fault was seeded. The hook stderr is captured by piping a PostToolUse payload
for `src/features.py` into `.claude/hooks/check_leakage.sh` by hand,
which reproduces exactly what the agent received in-session. The fix was then made
by the agent in a fresh session from the prompt: "make test is failing. Find the
cause and fix it. Do not edit anything in tests/ or src/config.py."

**Who did what.** The local agent seeded each fault and attempted each fix. The
capture of test and hook output, this write-up, and the tests added for the
feature and for Fault 3 were drafted with Claude Opus 5.5 in the claude.ai app,
from my real terminal output; I ran every command, reviewed every change, and
made the calls to reject agent fixes. See Attribution in REPORT.md.

## Feature test written first: `cnt_lag_2`

Before `cnt_lag_2` existed, the agent wrote
`tests/test_leakage.py::test_cnt_lag_2_is_true_calendar_lag`, which asserts that
`cnt_lag_2` on 2012-03-15 equals the raw `cnt` on 2012-03-13. Its first draft
wrapped the assertion in `if target_date in ...:`, so it would have passed without
checking anything if the date were missing; I rejected that draft and required a
version that asserts the date is present. Committed alone in "Failing test for
cnt_lag_2", before the feature. Failing run (`python -m pytest tests/test_leakage.py -q`):

```
        try:
            return self._engine.get_loc(casted_key)
        except KeyError as err:
            if isinstance(casted_key, slice) or (
                isinstance(casted_key, abc.Iterable)
                and any(isinstance(x, slice) for x in casted_key)
            ):
                raise InvalidIndexError(key) from err
>           raise KeyError(key) from err
E           KeyError: 'cnt_lag_2'

.venv/lib/python3.12/site-packages/pandas/core/indexes/base.py:3648: KeyError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_cnt_lag_2_is_true_calendar_lag - KeyError:...
1 failed, 7 passed in 0.40s
```

It fails for the right reason: the column does not exist yet. After
"Add cnt_lag_2" it passes.

## Fault 1: a forbidden column added to `feature_columns`

**Change** (seeded by the agent on request):

```diff
diff --git a/src/features.py b/src/features.py
index 02e93ca..793c0c1 100644
--- a/src/features.py
+++ b/src/features.py
@@ -82,7 +82,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["casual"]
 
 
 if __name__ == "__main__":
```

**Caught by:** `tests/test_leakage.py::test_no_forbidden_features`, during the
seeding session itself. The hook fired immediately after the edit landed and the
failure was shown to the agent as a system message before it could continue.

**Red test output** (`make test`):

```
......F.........                                                         [100%]
=================================== FAILURES ===================================
__________________________ test_no_forbidden_features __________________________

feats =         dteday  instant  season  ...  cnt_lag_2 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      959.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1341.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_2', 'cnt_lag_7', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 15 passed in 1.63s
```

**Hook stderr** (exit code 2, so the failure is returned to the agent):

```
Leakage tests failed after editing /Users/gabrielmaayah/Desktop/DSC180AB/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_2 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      959.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1341.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'casual'}
E       assert not ({'atemp', 'casual', 'cnt_lag_1', 'cnt_lag_2', 'cnt_lag_7', 'cnt_roll_7', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 7 passed in 0.28s
hook exit code: 2
```

**Agent fix:** one prompt, no follow-up needed. The agent found the appended
`+ ["casual"]` on line 85, removed it, ran the tests once and reported them green
(3 min 27 s wall clock). No permission prompts appeared: the session was in
Claude Code's auto mode, which ran the edit and the test run without asking.
(Claude Code switched between auto and manual mode across sessions; the mode did
not change what the hook caught.)
After the fix, `make test` returns 16 passed and `git status` shows no change to
`src/`.

## Fault 2: `.shift(1)` deleted from `cnt_roll_7`

**Change** (seeded by the agent on request):

```diff
diff --git a/src/features.py b/src/features.py
index 02e93ca..a03a88d 100644
--- a/src/features.py
+++ b/src/features.py
@@ -74,7 +74,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_2"] = out[TARGET].shift(2)
     out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
 
     return out.dropna().reset_index(drop=True)
```

**Caught by:** `tests/test_leakage.py::test_rolling_mean_excludes_today`. The hook
fired in the seeding session as soon as the edit landed. Without the shift, the
7-day mean on the checked date includes that day's own count (4389.0 instead of
the mean of the seven prior days, 4414.86), so the feature now contains the target.

**Red test output** (`make test`):

```
feats =         dteday  instant  season  ...  cnt_lag_2 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      959.0...    1787.0  1531.428571
713 2012-12-31    731.0  WINTER  ...     1341.0     920.0  1789.857143

[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 15 passed in 1.33s
```

**Hook stderr** (exit code 2):

```
Leakage tests failed after editing /Users/gabrielmaayah/Desktop/DSC180AB/bikeshare-open/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.28s
hook exit code: 2
```

**Agent fix:** one prompt, no follow-up needed, 4 min 45 s. The agent did not
restore the original line. It wrote
`out[TARGET].rolling(LAG_WARMUP).mean().shift(1)`, which rolls first and shifts
after. That form gives the same values here (the mean of days d-7 to d-1) and the
tests went green, but it breaks the CLAUDE.md rule "must `.shift(1)` before it
aggregates", which exists so the order is obvious on review. I rejected the agent's
version and restored the committed line with `git checkout src/features.py`; tests
green, 16 passed. Lesson: a passing test proves the values, not that the agent
followed the project's conventions.

## Fault 3: the `raise` removed from `encode_weather`

**Change** (seeded by the agent on request; it removed the whole guard):

```diff
diff --git a/src/features.py b/src/features.py
index 02e93ca..049bf1d 100644
--- a/src/features.py
+++ b/src/features.py
@@ -24,10 +24,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
     days -- the most interesting days in the dataset -- disappear with no
     error and no warning.
     """
-    known = series.dropna()
-    unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
 
 
```

**Caught by: nothing, at first.** With the guard gone, the full suite stayed
green and the hook passed silently:

```
$ make test
................                                                         [100%]
16 passed in 1.48s
```

```
hook stderr: (empty)
hook exit code: 0
```

Every weather label in the current data (GOOD / MISTY / BAD) is valid, so no test
ever passed the encoder an unknown label. The row-loss bound in
`test_contract.py` only notices a silent NaN if the data actually contains a bad
label. The guard was protecting against a case the suite never exercised.

**Closing the gap.** With the fault still in place, I added
`test_weather_encoder_rejects_unknown_labels` to `tests/test_leakage.py`. It
feeds `encode_weather` the series `["GOOD", "SNOW"]` and requires a
`ValueError`. It goes in `test_leakage.py` so the PostToolUse hook runs it on
every `src/` edit. Re-run with the fault still seeded:

```
$ make test
.............F...                                                        [100%]
=================================== FAILURES ===================================
_________________ test_weather_encoder_rejects_unknown_labels __________________

    def test_weather_encoder_rejects_unknown_labels():
        """An unseen weather label must raise, not become NaN. Every label in the
        current data is valid, so without this test nothing exercises the guard:
        deleting the raise in encode_weather leaves every other test green, and a
        new label would turn into NaN and be dropped by dropna() without warning."""
        from src.features import encode_weather
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:87: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unknown_labels - F...
1 failed, 16 passed in 1.13s
```

**Hook stderr** (exit code 2: the hook now catches this fault):

```
Leakage tests failed after editing /Users/gabrielmaayah/Desktop/DSC180AB/bikeshare-open/src/features.py:
........F                                                                [100%]
=================================== FAILURES ===================================
_________________ test_weather_encoder_rejects_unknown_labels __________________

    def test_weather_encoder_rejects_unknown_labels():
        """An unseen weather label must raise, not become NaN. Every label in the
        current data is valid, so without this test nothing exercises the guard:
        deleting the raise in encode_weather leaves every other test green, and a
        new label would turn into NaN and be dropped by dropna() without warning."""
        from src.features import encode_weather
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:87: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_encoder_rejects_unknown_labels - F...
1 failed, 8 passed in 0.28s
hook exit code: 2
```

**Agent fix: failed.** From the usual prompt, the agent replaced the guard with
`if result.isna().any(): raise ValueError(...)` after the `.map()`. That rejects
*every* NaN, including the legitimate one `reindex_to_calendar` inserts for the
missing day 2011-03-10, so `build_features` raises on the real data. The agent
then spent its time debugging errors its own fix created (a pandas `TypeError`).
I interrupted it after about 25 minutes with no working fix, and restored the
committed encoder with `git checkout src/features.py`. 17 passed. The original
guard checks labels on `series.dropna()` for exactly this reason: a missing day
is expected, an unknown label is not.
