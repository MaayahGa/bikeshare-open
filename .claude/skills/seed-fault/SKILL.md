---
name: seed-fault
description: Seed a deliberate fault in the pipeline, record which check catches it (tests, hook), restore, and write it up in docs/SEEDED_FAULTS.md. Use when asked to break the pipeline on purpose, test the verification suite, or seed a fault.
allowed-tools: Read, Edit, Bash(git status*), Bash(git diff*), Bash(git checkout -- src/*), Bash(git checkout -- data/raw/*), Bash(make test*), Bash(python -m pytest*), Bash(bash .claude/skills/seed-fault/capture.sh*)
---

# Seeding a fault: $ARGUMENTS

A suite that stays green under a seeded fault is not a verification suite. This
workflow breaks one thing on purpose and records, with real output, what caught
it. Follow the steps in order and paste output, never a description of it.

1. **Precondition.** Run `git status --short src/ data/raw/ tests/`. If anything
   is listed, STOP and say so: step 5 restores these paths and would destroy
   uncommitted work.

2. **Predict.** In one sentence each: which test in `tests/` should go red, and
   whether the PostToolUse hook (which runs only `tests/test_leakage.py`, only
   after an Edit/Write to `src/*.py`) should fire. If you predict nothing will
   catch it, say so; that is a finding, not a failure.

3. **Seed.** Make the single smallest edit that introduces the fault described in
   $ARGUMENTS. Never edit `data/raw/` with the Edit tool (it is denied); never
   touch `tests/` while seeding. If the hook fires, quote its message verbatim.

4. **Capture.** Pick a short slug for the fault (e.g. `drop-shift`) and run
   `bash .claude/skills/seed-fault/capture.sh <slug> <edited-file>`.
   Report the last lines it prints: tests passed/failed, hook exit code.
   Exit code 2 means the hook catches this fault; 0 means it does not.

5. **Restore.** `git checkout -- src/` (and `git checkout -- data/raw/` if the
   fault touched raw data). Run `make test` and confirm everything passes.
   Do not "fix" the fault by writing new code: restoring the committed version
   is the fix, so the agent cannot introduce a second bug while repairing the first.

6. **Write up.** Append a section to `docs/SEEDED_FAULTS.md`:
   `## Fault: <what was broken>`, then the diff, the red test output and the hook
   stderr from `notes/faults/<slug>/`, pasted in code blocks, and one line saying
   whether the prediction in step 2 held.

If nothing went red, stop after step 6 and recommend the test that would have
caught it. Do not add that test yourself unless asked.
