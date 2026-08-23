---
id: 67
title: The TypeScript starter guide is missing a section the other three have
status: done
priority: 3
refs: eval/judge/starter_parity.py agents_md headings, tasks/49
done_when: either the ts guide gains the missing section and starter_parity reports the heading sets equal, or the divergence is recorded as deliberate in the capability register with the reason; and verify_blind, starter_parity and starter_gate_control are re-run
established_by: 'The ticket premise is false: the ts guide carries the one-command contract under the heading Commands at line 8, same position, same sentence (just verify green means done, red means not done, nothing else is evidence). No starter edited, no regime boundary, eval/RUNS.md untouched. The second row is the same shape inverted: unity carries Gameplay is not correctness as a bold paragraph at eval/starters/unity/AGENTS.md:123, so starter_parity still reports it absent from unity headings, contradicting the ticket re-measurement claim. Repaired the instrument instead: ADJUDICATED_HEADINGS plus heading_findings in eval/judge/starter_parity.py record the verdict AND the sentence that carries the guidance, and re-read that sentence out of all four guides every run, so the tool goes red if an adjudication stops being true and notes a register entry whose row stops firing. parity_selftest 23 of 23 pass, up from 10, including the variant that matters - ts contract sentence deleted, heading still absent, tool must go red - which the pre-change code cannot produce at all. Gates re-run unpiped: starter_parity exit 0, verify_blind exit 0 on all four starters copied outside the repo (in-repo it is structurally red on ancestor reachability, now documented in eval/judge/AGENTS.md), starter_gate_control exit 1 with 1 of 29 FAILED - godot pristine verify test-render, pre-existing and independent since git diff main on eval/starters is empty, filed as task 80. Also filed task 78: only the rust guide mentions the Stop hook, which is live in all four.'
---

## What this is

Each of the four starters ships an `AGENTS.md` — the guide a building agent reads during a trial.
The four are deliberately **not** byte-identical: each is stack-native. But they are meant to
cover the same ground, and `eval/judge/starter_parity.py` measures how far apart they are.

## What is wrong, and how we know

`starter_parity` has collected each guide's **heading set** since it was written, named it in its
own docstring, and compared it with nothing. Task 49 wired the collection to a report — and it
immediately surfaced a forgotten copy.

Measured 2026-08-23:

| section | rust | ts | unity | godot |
|---|---|---|---|---|
| "The one command" | yes | **NO** | yes | yes |

Three guides tell the agent about the one-command contract; the TypeScript guide does not.

("Gameplay is not correctness" was reported by task 49 as missing from unity and is **present in
all four** on re-measurement — that half does not reproduce, and the re-measurement is why this
ticket says so rather than repeating it.)

## Why it matters

This is the **forgotten-copy** shape: four documents maintained in parallel, an edit landing in
three of them, and nothing comparing them. It is the same failure as the deleted skills mirror
(#99) with the copies still live.

The specific cost is one-arm: if the one-command contract is guidance that changes what an agent
does, the TypeScript arm has been running without it, and that is a difference between arms
nobody chose. Whether it *does* change behaviour is unmeasured — say so rather than assuming
either way.

## What should be done

Read the section in the three guides that have it, and decide whether the TypeScript arm's
absence is an oversight or deliberate — the TS toolchain genuinely differs, so "deliberate" is a
real possibility and a legitimate close.

**Either way is a regime boundary if you edit a starter**: `verify_blind.py`,
`starter_parity.py`, `starter_gate_control.py`, and a note in `eval/RUNS.md`. All four gates were
green as of 2026-08-23 and must be re-run.

If the divergence is deliberate, record it where `starter_parity` already reports deliberate
divergence rather than drift — the capability register it prints, which cites `DECISIONS.md`.

## What not to conclude

**Do not make the four guides identical.** `DECISIONS.md` records that they are stack-native by
design, and a parity gate over their prose would fail on correct input, which is how a gate gets
disabled. The question is whether a specific section is missing by accident, not whether the
documents match.

---

## What was found, 2026-08-23 — the title of this ticket is wrong

**The section is not missing. No starter was edited.**

The ts guide opens with `## Commands` at line 8 — the same position as `## The one command` in the
other three, first section straight after the identical preamble — and it carries the same
contract:

| guide | heading | the sentence |
|---|---|---|
| rust | `## The one command` | "`just verify` green means done; red means not done. Nothing else counts as evidence…" |
| ts | `## Commands` | "`just verify` green means done. Red means not done. Nothing else is evidence…" |
| unity | `## The one command` | "Green means done. Red means not done. Nothing else counts as evidence…" |
| godot | `## The one command` | "Green means done. Red means not done. Nothing else counts as evidence…" |

A heading rename, not a forgotten copy. The one-arm cost this ticket feared does not exist: **no
arm ran without the one-command contract.**

**The other half of the ticket is also wrong, in the opposite direction.** It says "Gameplay is
not correctness" is present in all four *on re-measurement* and does not reproduce. Re-run here,
`starter_parity` still reports it absent from unity — because unity carries it as a **bold
paragraph at the end of `## Testing`** (`eval/starters/unity/AGENTS.md:123`), not under its own
heading. The ticket measured *content* and the tool measures *headings*, and neither said which.
Both rows are the same shape: same guidance, different structure.

**So the defect is in the instrument, not in the guides.** The near-miss note keys on heading
text — the one thing `starter_parity`'s own comment says equality may not be demanded of — and it
printed *"check whether this is a section one guide never got"* on two rows that were both
answered no, and would have re-printed it every run forever. A check that asks a question it
cannot answer is not a check.

## What was changed

Nothing under `eval/starters/`. No regime boundary; `eval/RUNS.md` untouched.

- `eval/judge/starter_parity.py` — `ADJUDICATED_HEADINGS` plus a pure `heading_findings()`. A
  near miss is looked up, and the adjudication is then **verified against the guides**: the entry
  names the sentence that carries the guidance, and it must be present in all four every run. If
  it is absent from the stack that lacks the heading, that is the forgotten copy and the tool goes
  **red**; absent from a stack that has the heading, the entry names the wrong sentence and it
  also goes red. An entry whose row stops firing is noted as removable. Unadjudicated rows stay
  notes, so a legitimate rename cannot turn the gate red (#44, #57, #72).
- `eval/judge/parity_selftest.py` — 13 new expectations, both directions. The one that matters is
  the **variant**: ts's contract sentence deleted, heading still absent, tool must go red. The
  pre-change code prints the identical note either way, so a mutant of it establishes nothing.
- `eval/judge/AGENTS.md` — where to point `verify_blind.py`, see below.
- `eval/AGENTS.md` — the near-miss axis is adjudicated, and why unadjudicated rows stay notes.

## Two things the next agent must not re-derive

**1. `verify_blind.py` run against an in-repo starter is red for all four stacks, always.** Check
2 walks every ancestor for `judge/`, and `eval/starters/<stack>` has `eval/judge/RUBRIC.md` up its
path. Copy the starters somewhere outside the repository and pass those paths — done that way it
is **green on all four** (canary absent, rubric unreachable, 81 criterion ids absent). The error
text points at `--work-root`, which is `wholegame.py`'s flag, not this tool's. Now recorded in
`eval/judge/AGENTS.md`.

**2. `starter_gate_control.py` is at `eval/tools/`, not `eval/judge/`,** and the claim above that
"all four gates were green as of 2026-08-23" does not hold for godot: the row `godot: GREEN on
pristine (the same just verify must also exit 0)` **FAILED**, `just verify` exiting 1 on a
pristine tree. It cannot be caused by this task's change — the only files touched are two in
`eval/judge/`, and `starter_gate_control.py` imports neither. Pre-existing and unrelated; filed
separately.

## What was deliberately not changed, and why

The ts heading was **not** renamed to `## The one command`. That is a starter edit — a regime
boundary, an `eval/RUNS.md` note, three gates — bought for a cosmetic convergence, on documents
`DECISIONS.md` says are stack-native by design and this ticket says must not be made identical.
It would also not have fixed the unity row.

**A real one-arm asymmetry was found and left alone, because it is out of scope:** rust's guide is
the only one of the four that tells the agent *"A Stop hook re-runs it when you try to finish, so
ending the turn red does not work."* The hook is live in all four — `.claude/hooks/verify-gate.sh`
present and wired under `"Stop"` in all four `.claude/settings.json` — so three arms run a
mechanism their guide never mentions. That is 1-of-4, so the near-miss heuristic cannot see it,
and it is a sentence rather than a heading. Filed separately.
