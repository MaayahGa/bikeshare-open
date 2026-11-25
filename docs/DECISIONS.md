# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-25: Added `cnt_lag_2` (cnt two calendar days before d). Available at prediction time for d; built after reindex_to_calendar so the 2011-03-10 gap stays NaN. Validation R^2: ridge 0.6475 -> 0.6453 (-0.002; MAE 832.9 -> 833.4), hgb 0.2185 -> 0.2481 (+0.030). Below the skill's +0.01 bar for ridge, the model we report. Kept: the ridge change is inside validation noise, it helps hgb, and its test guards the lag alignment. Reported as a null result for ridge. Test set not consulted. The local agent's draft of this line gave no availability argument; rewritten with Claude Opus 5.5 (claude.ai) and checked by me.
