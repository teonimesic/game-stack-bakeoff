---
id: 78
title: Only the rust guide tells the agent the Stop hook re-runs verify; the hook is live in all four
status: done
priority: 3
refs: eval/starters/*/AGENTS.md, eval/starters/*/.claude/settings.json, tasks/67
done_when: either the three guides that omit it gain the sentence and starter_parity plus verify_blind and starter_gate_control are re-run with an eval/RUNS.md regime note, or the omission is recorded as deliberate with the reason and a measurement of whether the sentence changes what an agent does
established_by: 'Branch one of the done_when. ts, unity and godot AGENTS.md gained the Stop-hook sentence in stack-native wording; rust already had it. eval/RUNS.md carries it as the FIFTEENTH comparability break, a three-arm break and the first of that shape. DECISIONS.md gains the rule the omission violated: stack-native covers stack facts, never harness facts. Gates: verify_blind BLIND exit 0 on out-of-repo copies of all four, 81 criterion ids, 4 trees; starter_parity exit 1 BEFORE the guide edits with one finding naming exactly godot, ts, unity and exit 0 after, guides 2032-2273 words; starter_gate_control 29 measurements 1 FAILED 0 NOT CHECKED, the failure being godot pristine verify test-render which task 67 already measured FAILED before this task and filed as task 80, while the row that would catch a defect from THIS change - UNCHANGED by its own just verify on a pristine tree, the check that matters because ts runs prettier over the tree inside verify - is green on all four; docstat --sweep clean exit 0; tasks.py check 88 tasks well-formed. The measurement the ticket asked for is a NULL and the reason is stated rather than hidden: across the 12 trials with a stored starter baseline that reached a stop the Stop gate blocked 0 times in BOTH arms, 0 of 4 rust and 0 of 8 the other three, so the outcome has no variance in the only population where the exposure is provable. 19 transcripts in the whole archive carry a block and all 19 are dated 2026-08-11 or 2026-08-12. Extraction proved on one row known in advance, g1_pong rust t0 with exactly 2 blocks, and the naive grep for the reason text was rejected because a g4c ts trial cats the hook file. Measured live at CLI 2.1.220 with the harness flags, two arms at 0.03 USD: a blocking Stop hook writes Stop hook feedback into the transcript and the agent complies, a Stop hook that exits 0 writes nothing anywhere, so no-block cannot separate a green gate from a gate that never ran - filed as tasks 84 and 86, and task 88 for README''s stale thirty-seven findings against a log reaching 129. New durable check: starter_parity.mechanism_findings, keyed on every event wired in every settings.json rather than on the word Stop, with parity_selftest at 60 expectations 0 failed, up from 44, a mutant per guide and three variants including PreToolUse wired everywhere and named nowhere. One selftest control failed first time because its substitution never matched and was repaired rather than relaxed. Branch task-78-stop-hook-named-in-every-guide, commit 54bca4c.'
---

Measured 2026-08-23 under task 67. All four starters ship .claude/hooks/verify-gate.sh and wire it under "Stop" in .claude/settings.json, so the gate re-runs at end-of-turn in every arm. Only eval/starters/rust/AGENTS.md line 12 says so: 'A Stop hook re-runs it when you try to finish, so ending the turn red does not work.' ts, unity and godot guides never mention it - grep for 'Stop hook' across the four hits rust only.

Why it matters: this is the one-arm difference task 67 went looking for and did not find. An agent that knows ending red does not work has a reason to run verify before finishing; three arms are not told. Whether that changes behaviour is UNMEASURED - say so rather than assuming. The stored trials can be asked: agent.final_text and the transcripts record whether an arm hit the Stop gate and had to go back.

Why the existing gate cannot see it: starter_parity's near-miss heading check fires only on a heading present in every guide but one. This is a SENTENCE, present in one guide of four. The heading axis is structurally blind to both - to 1-of-4, and to anything below heading level.

Do not make the four guides identical (DECISIONS.md: stack-native by design). The question is whether this specific guidance was meant to reach every arm.

---

## What was done, 2026-08-23 — branch one of the done_when

The three guides gained the sentence, in stack-native wording. `eval/RUNS.md` carries it as the
FIFTEENTH comparability break (the ordinal was free: the `template*/` deletion section says
explicitly that it is *not* a fifteenth boundary). `DECISIONS.md` gained the rule the omission
violated: **stack-native covers stack facts, never harness facts.** `eval/AGENTS.md` gained the
axis note.

The premise was re-checked before acting, not assumed: the four `.claude/settings.json` are
byte-identical and all wire `"Stop"`; `wholegame.py:200` passes `--setting-sources project`, which
is what loads them; `grep 'Stop hook'` over the four guides hit `starters/rust/AGENTS.md:12` only.
All true as written.

## The measurement the ticket asked for comes back NULL

**Not "the effect is small". The outcome variable has no variance in the population where the
exposure is provable.**

A Stop-hook block appears in a transcript as a `user` entry with `isMeta: true` whose content
begins `"Stop hook feedback:"`. **Do NOT grep the reason text** — an agent that runs
`cat .claude/hooks/verify-gate.sh` puts the same words in a `tool_result`, and one g4c ts trial
does exactly that. The extraction was proved on one row whose answer was known in advance
(`g1_pong__rust__t0`, 2026-08-12 `wholegame-work`: exactly 2 blocks, both read by hand).

Joining trial records x stored per-trial starter baselines x transcripts:

| population | trials | blocks |
|---|---|---|
| stored baseline, guide MENTIONS the hook (rust) | 4 | 0 |
| stored baseline, guide SILENT (ts, unity, godot) | 8 | 0 |

20 trials have a stored starter baseline (`wg-g4`, `wg-g4b`, `wg-g4c` — no earlier run stores one,
so no earlier run can establish what its guides said). 12 reached a stop; the other 8 are
`wg-g4b`'s `api_error` population. All 22 baselines confirm the asymmetry historically:
`guide_mentions_stop_hook` true for rust, false for the other three, `"Stop"` wired in all 22.

Across the whole transcript archive only **19** transcripts carry any block, every one dated
2026-08-11 or 2026-08-12. None from `wg-matrix` (2026-08-13) onward.

## THE THING THE NEXT AGENT MUST NOT RE-DERIVE

**An exit-0 Stop hook leaves NO trace anywhere.** Measured directly at CLI 2.1.220 — the version
every stored transcript records — with the harness's own flags
(`--setting-sources project --strict-mcp-config --exclude-dynamic-system-prompt-sections
--permission-mode acceptEdits`), two arms, $0.03 total:

| arm | hook | transcript | log the hook wrote itself |
|---|---|---|---|
| A | blocks until a file exists | `Stop hook feedback: ...` present; the agent complied and created it | 2 invocations |
| B | identical wiring, exits 0 | **nothing** | 1 invocation |

So `--setting-sources project` really does honour a project Stop hook (arm A), **and** "no block
in the transcript" is equally consistent with *the gate ran and passed* and with *the gate never
ran* (arm B). No stored artifact separates them. Task 67's "the hook is live in all four" rests on
file presence, which is rule 2. What IS established is that the per-stack warm guards cannot have
short-circuited in `wg-g4c`: `node_modules` (ts), `Library` (unity), `CARGO_TARGET_DIR` (rust) and
`just` on `PATH` (godot) all held in the live work trees.

Filed as **task 84** (give the hook an audit trail — with the constraint that the trial tree
becomes the graded diff, so the log must land outside it) and **task 86** (number the finding; no
number was taken here because 11 worktrees were live and 11 collisions happened this day).

## The axis, and why the heading axis could never have caught this

`starter_parity.mechanism_findings()` — every hook event wired in EVERY starter's
`.claude/settings.json` must be named in EVERY `AGENTS.md`. Keyed on the wired event, never on the
word "Stop", so the next hook is covered. An event wired on some stacks only is a stack choice,
reported and never failed; an empty intersection says it compared nothing rather than reporting
agreement.

Red before the guide edits (exit 1, one finding, naming exactly `['godot', 'ts', 'unity']`), green
after. `parity_selftest.py` 60 expectations 0 failed, up from 44: the mutant is the sentence
removed from each guide in turn (4 red); the variants are `PreToolUse` wired everywhere and named
nowhere (must go red, or the check is about the word "Stop"), both words present but far apart
(must NOT count), and *"a hook on Stop"* (must still count).

One control in that set **failed first time and was repaired rather than relaxed**: the
reworded-guide check substituted a phrase the guide breaks across a line, so the guide was
unchanged and the expectation passed for the wrong reason. It now asserts the substitution
happened before asserting what follows from it.

## Gate results

- `judge/verify_blind.py` — **BLIND, exit 0**; canary, rubric and 81 criterion ids absent from 4
  trees and every ancestor. Run against copies **outside the repository**; in-repo it is
  structurally red for all four (task 67).
- `judge/starter_parity.py --skip-tests` — **exit 1 before** the guide edits with one finding
  naming exactly `['godot', 'ts', 'unity']`, **exit 0 after**; guides 2032–2273 words.
- `tools/starter_gate_control.py` — **29 measurements, 1 FAILED, 0 NOT CHECKED**, exit 1. The
  failure is godot's pristine `just verify` (`test-render` exit 1), **already FAILED before this
  task** — task 67 measured it and filed `tasks/80`. `git diff main -- eval/starters` is three
  markdown sentences and the tool reads none of them. The row that *would* have caught a defect
  from this change is green on all four: **UNCHANGED by its own `just verify` on a pristine
  tree**, which is the check that matters because ts runs prettier over the tree inside `verify`
  and a reformatted `AGENTS.md` is exactly the #106 shape.
- `docstat.py --sweep` — **exit 0**, sweep clean over 140 docs. (Its `--renumbered` companion
  reports 33 pre-existing `#119` citations across the corpus; none of them are in anything written
  here, and nothing added by this task cites a finding number at all.)

## Where the working files are

The census scripts are in this session's scratchpad, not the repo — they are one-shot and their
outputs are quoted above. What matters is reproducible from the description: the block signature,
the join of `eval/runs/*/trials/*.json` x `eval/runs/*/starter-baselines/*.tar.gz` x
`~/.claude/projects/*/**.jsonl`, and the two probe arms. Read baselines with python `tarfile`, not
`bsdtar` — macOS bsdtar rejects GNU tar's wildcard option, and the `|| true` idiom wrapped around
that failure returned 0 for all 20 rows once already (AGENTS.md rule 12 table).
