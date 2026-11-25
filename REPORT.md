# Forecasting daily bikeshare demand: an agent-built pipeline, verified

Gabriel Maayah · DSC 180A · Agentic Programming assignment

## Results

Validation (H1 2012) and test (H2 2012) scores after training on 2011, from
`make all`. "Before" is the starter pipeline (14 features); "after" adds my
feature `cnt_lag_2` (15 features) and is what `reports/metrics.json` contains.
R^2 is measured against each split's own mean, so 0 means "as good as a constant
nobody could have known in advance".

| model | features | valid R^2 | valid MAE | test R^2 | test MAE |
|---|---|---|---|---|---|
| baseline_mean | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_mean | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| baseline_persistence | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| baseline_persistence | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| ridge | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| ridge | after | 0.6453 | 833.4 | 0.583 | 945.5 |
| hgb | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| hgb | after | 0.2481 | 1269.8 | -0.4737 | 1947.9 |

The baselines do not use the feature set, so their rows do not change. The
"after" rows match `reports/metrics.json` to the printed digit.

## Headline finding

The naive evaluation, with `casual` and `registered` left in the features
(`python -m src.leakage_demo`), gives test R^2 = 1.000000 and is invalid: `casual + registered == cnt`
exactly, so the model learns addition. Under a temporal split with those columns
excluded, the mean baseline scores -2.14 on test because ridership grew about 65%
from 2011 to 2012. Ridge reaches 0.583, against 0.510 for persistence ("predict
yesterday's count"), and it loses to persistence on MAE (945.5 vs 840.1 rides).
Gradient boosting scores -0.47 because a tree cannot predict above the largest
count it saw in training: 104 of the 184 test days (57%) are above the 2011
maximum of 6,043 rides. My
feature `cnt_lag_2` changed ridge's validation R^2 by -0.002 (inside the noise of
a 182-day validation set) and hgb's by +0.030. I kept it, reported it as a null
result for ridge, and kept its test because that test guards the lag alignment.

## Exercise 4: target transformation

Gradient boosting fails here because of the trend, not the features, so I changed
what it predicts: `cnt / cnt_roll_7`, today's count relative to the previous
seven days, multiplied back by `cnt_roll_7` at prediction time
(`python -m src.train --target ratio`; off by default, so `reports/metrics.json`
is the untransformed pipeline). The ratio sits near 1 in both years, so the tree
no longer has to extrapolate. `cnt_roll_7` is shifted before it is rolled, so
nothing from day d is used to predict day d.

| target = cnt / cnt_roll_7 | valid R^2 | valid MAE | test R^2 | test MAE |
|---|---|---|---|---|
| hgb | 0.7527 | 677.9 | 0.6247 | 831.2 |
| ridge | 0.3905 | 1092.9 | 0.0257 | 1493.8 |

I judged it on validation first, where hgb went from 0.2481 to 0.7527, and then
looked at the test set exactly once (`--show-test`). Ridge gets worse under the
same transform: its lag inputs are still in raw counts, and a linear model cannot
map them onto a ratio, whereas the tree can. **Verdict: defensible, but the win
is small.** It uses only information available at prediction time, it targets
the mechanism we had already identified, and it was the only transformation I
tried. Against it: it was chosen after seeing hgb fail, it changes the loss from
squared error in rides to squared error in the ratio, and on test it beats
persistence by only 9 rides of MAE (831.2 vs 840.1), well within what a
different 184-day window could reverse. It shows the tree's failure was the trend;
it does not show that the tree is a better forecaster.

## Exercise 5: ridge vs persistence

Ridge is worth deploying over "yesterday again", narrowly. On the test set it
explains more variance (R^2 0.583 vs 0.510) but has a larger average error
(MAE 945.5 vs 840.1 rides). On validation it wins on both (0.6453 / 833.4 vs
0.4507 / 900.6). R^2 is based on squared error, so it is driven by the large
misses. MAE is driven by the typical day. The two disagreeing on test means
persistence is closer on ordinary days, but ridge misses by less when demand
jumps, for example after a weather change, which persistence can only learn about
a day late. For an operator deciding how many bikes to rebalance, a large miss
(empty docks on a busy day) costs far more than being 100 rides off on a quiet
one, so I weight R^2. The honest size of the result is still small: a 0.07 R^2
gain from a model whose largest inputs are lagged demand. A cheaper alternative
worth testing is persistence corrected for day of week.

## Attribution

**Models.** All agent work in the repository was done by `qwen3.5:9b` via Ollama
(built as `bikeshare-coder`, 64k context) in Claude Code 2.1.332, on a 16 GB
MacBook Pro. I did not switch local models. I also used Claude Opus 5.5 in the
claude.ai app as an assistant outside the repo: it wrote code and docs that I
reviewed, ran and committed, listed below. Setup note: `make model` failed on
Ollama 0.40.18 (a Modelfile piped on stdin is not supported); I built the model
with `ollama create bikeshare-coder -f model/Modelfile`.

**Generated by the local agent (qwen3.5:9b):**
- `cnt_lag_2` in `src/features.py`, and `tests/test_leakage.py::test_cnt_lag_2_is_true_calendar_lag`. Its first draft had an `if` guard that could never fail; the final version uses assertion text I supplied.
- Seeding all five faults in `docs/SEEDED_FAULTS.md`, the fix for Fault 1, the rejected fixes for Faults 2 and 3, and the first draft of the Fault 5 write-up.

**Generated by Claude Opus 5.5 (claude.ai), reviewed by me:**
- `RAW_FEATURE_COLS` and `SOURCE_COLS` in `src/config.py`, and `test_every_raw_column_is_classified`.
- `test_weather_encoder_rejects_unknown_labels`.
- The raw-data hash check: `RAW_SHA256`, `verify_raw()`, `test_raw_file_is_unmodified`.
- `RatioTarget` and the `--target` / `--show-test` flags in `src/train.py`.
- The `seed-fault` skill and its `capture.sh`.
- The text of `docs/SEEDED_FAULTS.md`, most `docs/DECISIONS.md` lines, the `CLAUDE.md` additions, and the draft of this report.

Everything else is the course starter.

**Decisions that were mine** (each is a dated line in `docs/DECISIONS.md`):
- what to predict (`cnt`, daily) and what counts as leakage (`casual`, `registered`), kept from the starter;
- how to split (2011 / H1 2012 / H2 2012) and which baselines (mean and persistence), kept from the starter;
- adding `cnt_lag_2`, and keeping it despite a null result for ridge;
- requiring every raw column to be classified;
- rejecting the agent's fixes for Faults 2 and 3 and restoring the committed code;
- closing the Fault 3 gap with a test, and the Fault 4 hash check;
- the Exercise 4 verdict and the Exercise 5 recommendation;
- whether the answer is believable: the honest result is a 0.07 R^2 gain over persistence, not "R^2 = 0.58".

**What the agent got wrong, and how it was caught:**
- a test that could not fail (rejected in review);
- an availability argument that was not one (rewritten);
- a Fault 2 fix that passed the tests but broke the project rule (rejected);
- a Fault 3 fix that broke on the legitimate 2011-03-10 gap (interrupted after 25 minutes);
- a false claim that no permission rule had stopped it in Fault 4, contradicted by the tool output.

In each case, a test result or printed output disagreed with what the agent said.
