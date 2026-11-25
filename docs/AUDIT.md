# Exercise 3: Leakage audit of a teammate's repository

## What was audited

- **Repository:** https://github.com/CocoXu08/DSC180A-Methodology-7 (branch `ma7-work`),
  shared by Ziling (Coco) Xu, a classmate in the course. I did not write any of this code.
- **Commit audited:** `90a97c7` ("Align report title with assignment instructions").
  Her commit history labels the assignment MA6, and the repo is built on the same
  bikeshare starter.
- **Date:** 2026-11-25.
- **How:** cloned into a scratch directory (`/tmp/coco-audit`), using my existing venv.
  `make all` ran and `make test` gave 18 passed before the audit started. The auditor
  was started directly as the subagent:
  `claude --model bikeshare-coder --agent leakage-auditor`, with the prompt
  "Audit this repository. Run your checks and report your findings."
- **Model:** qwen3.5:9b via Ollama (`bikeshare-coder`, 64k context), Claude Code 2.1.332.
- **Run:** 39 min 17 s, 8 files read, 26 shell commands (7 failed). Every command was
  approved by hand. The auditor's tools (Read, Grep, Glob, Bash) include no Edit, and
  nothing in the clone was changed.
- **First attempt discarded:** an earlier session, asked to "use the leakage-auditor
  subagent", launched a `general-purpose` agent instead and stalled for 22 minutes
  with API retries. I stopped it and restarted with `--agent leakage-auditor`.

## The auditor's output (verbatim)

Exported with `/export` from the Claude Code session. The tool calls are collapsed in
the export; their summary line is part of the output.

```
❯ Audit this repository. Run your checks and report your findings.              

  Thought for 13s (ctrl+o to expand)

⏺ I'll audit this repository systematically. Let me start by reading
  src/config.py to understand the forbidden columns and then examine the diff
  and implementation against the five critical checks.

  Thought for 38m 24s, read 8 files, listed 1 directory, ran 26 shell commands · 7 failed (ctrl+o to expand)

⏺ Auto mode can't check actions in this session. Its safety check runs 
  on the server, and your requests go through localhost:11434, which 
  doesn't pass it through. Actions that need the check now ask for your 
  approval. To work without these prompts, switch permission mode with 
  Shift+Tab. To use auto mode, ask whoever runs localhost:11434 to pass 
  Claude Code's server-side safety check through: https://code.claude.co
  m/docs/en/permission-modes#server-side-classifier-review

⏺ Audit Summary

  After reviewing the codebase against the five critical checks:

  All five checks PASS ✓

  1. Target leakage: The LEAKAGE_COLS correctly excludes casual, registered, and
     cnt. The feature_columns() function filters out all forbidden columns. The
     lagged features (cnt_lag_1, cnt_lag_7) are true calendar shifts of the
     target, not restatements. The identity casual + registered == cnt is
     verified in tests but never leaked to models.
  2. Temporal ordering: The temporal split uses temporal_split() which splits by
     date (train: 2011, valid: H1 2012, test: H2 2012), not randomly. All
     transformations (shift(), rolling()) apply .shift(1) before aggregation.
     Scaler is fit only on training data in the pipeline. No transformers see
     validation/test during .fit().
  3. Calendar gaps: The reindex_to_calendar() function creates a gap-free daily
     index from min to max date, and all lag/rolling features use .shift(1)
     before aggregating. Tests verify this with
     test_lags_are_true_calendar_lags, test_rolling_mean_excludes_today, and
     test_rolling_14_mean_excludes_today.
  4. Silent row loss: The only rows dropped are the LAG_WARMUP=14 initial days
     (which legitimately have no lag history) and missing calendar days (one day
     in 2011-03-10). This is bounded by test_only_expected_rows_are_dropped
     which asserts lost ≤ allowed.
  5. Unreported baseline: All four models (baseline_mean, baseline_persistence,
     ridge, hgb) report both mean baseline and persistence baseline on
     valid/test splits, including negative R² values. The metrics.json shows
     this explicitly for all models.

  No issues found that change a number or invalidate a conclusion.

✻ Baked for 39m 17s · done 12:48 PM
```

## My verdict

**I agree with the auditor's conclusion: nothing I found changes one of her numbers or
invalidates her conclusions.** I checked each of its claims against her code rather
than accepting its summary.

| Auditor claim | My check | Agree? |
|---|---|---|
| 1. `casual`, `registered`, `cnt` excluded; lags are true calendar shifts | `LEAKAGE_COLS` and `feature_columns()` unchanged from the starter; `test_no_forbidden_features` and `test_lags_are_true_calendar_lags` pass | Yes |
| 2. Temporal split; scaler fit on train only | `temporal_split` splits on `TRAIN_END` / `VALID_END` dates. The scaler is inside `make_pipeline(StandardScaler(), Ridge())`, so it is fit on 2011 only | Yes |
| 3. Shift before every rolling feature | `cnt_roll_7` and her added `cnt_roll_14` both use `.shift(1).rolling(...)`, each with its own test | Yes |
| 4. Only warm-up and the missing day lose rows | Conclusion right, explanation wrong. With `LAG_WARMUP = 14`, the missing 2011-03-10 also costs the 14 rows after it: 728 raw rows become 700 (28 lost), exactly the test's bound of 14 + 14 x 1. Not "one day". | Partly |
| 5. Both baselines reported | `reports/metrics.json` has mean and persistence on valid and test. Ridge test R^2 0.6268 vs persistence 0.5099; hgb is negative and reported | Yes |

**What the auditor missed (does not change a number today).** Her suite has the gap I
found in my own Fault 3: no test passes `encode_weather` an unknown label. I checked
this directly. With the `if unknown: raise ValueError(...)` lines deleted from her
`src/features.py`, her suite still gives 18 passed. Every label in the current data
is valid, so her numbers are unaffected, but a new label would become NaN and be
dropped without a warning. The auditor's instruction to report only findings that
change a number is why it is absent from its report. I would add a test like my
`test_weather_encoder_rejects_unknown_labels`.

**How far to trust the auditor's process.** Watching the approvals, several of its own
checks were wrong:
- It tested date membership with `date in feats.dteday`, which checks row index labels,
  not dates. This produced a false "Hurricane Sandy is missing" alarm that it then spent
  several checks chasing.
- One check printed "No differences found above means data is not leaking"
  unconditionally, whatever the comparison above it showed.
- One copied `cnt` onto the reindexed calendar by row position, which misaligns every
  day after the gap.

Its final summary happens to be right, but it is right because the code is sound, not
because these checks showed it. The evidence I rely on is her passing tests, the code
I read, and the two experiments above (the row count and the deleted `raise`).

*The verdict section was drafted with Claude Opus 5.5 (claude.ai), which cloned her
repo separately to verify each claim; I reviewed it and agree with it.*
