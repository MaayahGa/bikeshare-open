# Seeded faults (Exercise 2)

Each fault was seeded by the local agent (qwen3.5:9b via Ollama, 64k context) in
Claude Code, with the PostToolUse hook in `.claude/settings.json` active. The red
test output is `make test` (`python -m pytest tests/ -q`) run by hand right after
the fault was seeded. The hook stderr is captured by piping a PostToolUse payload
for `src/features.py` into `.claude/hooks/check_leakage.sh` by hand,
which reproduces exactly what the agent received in-session. The fix was then made
by the agent in a fresh session from the prompt: "make test is failing. Find the
cause and fix it. Do not edit anything in tests/ or src/config.py."

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
(3 min 27 s wall clock). No permission prompt appeared, including for the
edit, even though the status bar showed manual mode; `make` and `python -m pytest`
are pre-approved in `settings.json`, but the edit was expected to ask.
After the fix, `make test` returns 16 passed and `git status` shows no change to
`src/`.
