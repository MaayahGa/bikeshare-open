# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-25: Added `cnt_lag_2` (cnt two calendar days before d). Available at prediction time for d; built after reindex_to_calendar so the 2011-03-10 gap stays NaN. Validation R^2: ridge 0.6475 -> 0.6453 (-0.002; MAE 832.9 -> 833.4), hgb 0.2185 -> 0.2481 (+0.030). Below the skill's +0.01 bar for ridge, the model we report. Kept: the ridge change is inside validation noise, it helps hgb, and its test guards the lag alignment. Reported as a null result for ridge. Test set not consulted. The local agent's draft of this line gave no availability argument; rewritten with Claude Opus 5.5 (claude.ai) and checked by me.
- 2026-11-25: Classify every raw column in `src/config.py` (`RAW_FEATURE_COLS`, `SOURCE_COLS`) and test that none is unclassified. `feature_columns()` is a denylist, so a new numeric column would otherwise enter the model silently; shown by appending `new_sensor` to the raw file, which appeared in the feature list and turned the new test red.
- 2026-11-25: `/new-feature` could not run its `!python -c` feature-list line (blocked by permissions), so the skill's steps were followed by hand from SKILL.md. Left the skill as shipped.
- 2026-11-25: Fault 2: rejected the agent's fix (`rolling().mean().shift(1)`). Same values, tests green, but it breaks the CLAUDE.md rule to shift before aggregating. Restored the committed line.
- 2026-11-25: Fault 3: added `test_weather_encoder_rejects_unknown_labels` to `test_leakage.py`, so the hook runs it. Removing the encoder's raise had left the whole suite green. Rejected the agent's fix (raise on any NaN), which breaks on the legitimate 2011-03-10 gap row.
- 2026-11-25: Fault 4: added a sha256 check of the raw file (`RAW_SHA256`, `verify_raw()` in `make data`, `test_raw_file_is_unmodified`). Permission rules blocked `cp` but not `python -c shutil.copy`; the hook never sees Bash. Also noted that the starter's `Write(./data/raw/**)` deny rule never matches.
- 2026-11-25: Added the `/seed-fault <description>` skill (with `capture.sh`) for the break-capture-restore-write-up loop repeated for Faults 1-4. Its fix step is `git checkout`, not agent-written code, because the agent's own fixes were wrong in Faults 2 and 3.
- 2026-11-25: CLAUDE.md: added the raw-column classification rule, the raw-data hash rule and a Skills section (53 lines). `.gitignore`: stopped ignoring `reports/` and `audit.jsonl` so `metrics.json` and the audit are committed; ignore `notes/` (local evidence scratch).
