---
id: 46
title: Pre-register whether a required finish-report section changes what agents disclose
status: open
priority: 5
refs: 'AGENTS.md rule 11, eval/IMPROVEMENTS.md axis 2 candidate 5, eval/FINDINGS.md #98'
done_when: either the experiment has run on a fresh matrix and the pre-registered outcome table has been filled in, or it is closed as declined with the cost argument recorded in eval/RUNS.md
---

## What this thing is

Every whole-game trial ends with the building agent writing a free-form closing message. The
harness stores it **twice**: whole and untruncated as `.result` in `agent_result.json`, and
tail-truncated to its last 3000 characters as `agent.final_text` in `trials/<trial>.json`. (This
paragraph said `agent.final_text` was in `agent_result.json`; it is not, and that field is a
partial read of 43 of the 90 stored messages. Corrected 2026-08-23 — see `eval/AGENTS.md`,
"Reading the agent's own closing message".) Nothing in the evaluator reads either. The four
starters
(`eval/starters/{godot,rust,ts,unity}/AGENTS.md`) tell the agent what to build and what to verify;
none of them says anything about what its closing message must contain.

## What is wrong, and how we know

`AGENTS.md` rule 11 was written because four agents, unprompted, wrote a paragraph headed *"What
I could not verify — and why"* that named the exact mechanism behind a whole run's spread — and
the graders re-derived it independently. #98 is the second instance: both graded Godot agents in
`wg-g4c-2026-08-21T02-26-46` stated in their own words that the starter's gate was red before they
touched anything, and that is how the blast radius of that defect was eventually bounded.

So the disclosures exist, they are load-bearing, and they arrive **by luck**. An agent that does
not volunteer one is indistinguishable from an agent that had nothing to disclose.

`game-research-gpt`'s `template/AGENTS.md:102-113` requires the section instead of hoping for it:
player-visible behaviour delivered; design choices; exact verification commands and results;
*"screenshot/video/log/metric paths you personally inspected"*; remaining risks and anything not
verified on real hardware; and *"do not claim Windows, iOS, PS5 or Switch validation unless it
actually ran on that target."*

## Why it matters

The disclosure is the cheapest evidence in the run and it is the only channel through which the
subject can report something the instrument does not measure. Two of this project's more expensive
findings were recovered from it after the fact.

Nothing is blocked while this stands, which is why the priority is 5. It is filed so it is not
re-derived from scratch a third time.

## What should be done

**Do not install this quietly.** Editing `eval/starters/*/AGENTS.md` is a regime boundary: runs
before and after stop being comparable, `judge/verify_blind.py` and `judge/starter_parity.py` must
be re-run, and the boundary is recorded in `eval/RUNS.md`. It also costs a fresh matrix — read the
current figure out of `eval/RUNS.md` rather than quoting one from memory (rule 5).

So the first move is not a code change. It is to establish the baseline offline, for free:

1. **Measure the current disclosure rate.** Read `agent.final_text` from every stored
   `agent_result.json` under `eval/runs/**`. Classify each: does it name anything the agent could
   not verify, or any risk it is leaving behind? Report the rate **per stack and per run**, with
   `n` per group - a mean over completed and aborted trials together describes nothing (rule 4).
   Classification by hand is acceptable at this scale and is more trustworthy than a regex; record
   the rule used so someone can disagree with it.
2. **Only then** decide whether the experiment is worth a matrix.

### Pre-registration - fill this in BEFORE running anything

State what each outcome would mean, so that a null is a finding rather than a disappointment.

| baseline disclosure rate | what it means | next move |
|---|---|---|
| already high (say >70% across all four arms) | the instruction would change little; the disclosures are a property of the model, not of the prompt | close as declined, record the rate |
| low and **uniform** across stacks | a real gap, and a template change is the plausible fix | worth a matrix arm if one is being run anyway |
| low and **stack-correlated** | the more interesting result, and a warning: it would mean the arms differ in how much they tell us, which biases every after-the-fact reconstruction | investigate the correlation before changing any starter |

If the experiment does run, the change must land in **all four** starters in the same words, and
`starter_parity.py`'s AGENTS.md size-and-headings comparison must be re-run: a section added to
one arm is a helpfulness difference that would be attributed to the stack.

### What not to conclude

A higher disclosure rate after the change is **not** evidence that the work got better. It is
evidence that the reporting changed. Do not let it move any tier-1 or tier-2 number, and do not
report it beside one.

Also do not import the sibling instruction from `game-research-gpt` - *"translate every acceptance
phrase into an implementation state/action and an evidence check before coding"* - as part of this.
It is plausible and there is **no offline measurement that would show it helped**, because no
stored artifact records whether an agent decomposed the prompt. If it is ever run, it must be a
separate arm, or the two changes confound each other (rule 8).

---

## RESULT, 2026-08-23 — baseline measured, experiment DECLINED

Step 1 was done and it decided step 2. The full write-up, including the cost argument the
`done_when` requires, is in **`eval/RUNS.md`, "DECLINED: requiring a finish-report section in the
starters"**. Do not re-derive any of the below; it cost one careful pass over 90 messages.

**The classification rule, recorded so it can be disagreed with.** A trial *discloses* if its
closing message explicitly names, about the delivered work, either (a) something the agent could
not verify, did not run, or never executed, or (b) a residual risk, limitation, defect or unmet
requirement it is leaving behind. Success summaries, feature lists, uncaveated verification
results, "future enhancements" framed as optional extensions, and problems the agent hit **and
fully fixed** with no residual risk all score 0. Four of the 75 are arguable either way and are
marked BORDERLINE in the scratch classifier; flipping all four moves 41.3% to 46.7%.

**The headline.** 90 stored `agent_result.json`; **15 carry no message the agent wrote**; the
other **75 are all `completed`**; **31 of 75 (41.3%) disclose**, 10 of those under a dedicated
heading. Per stack: godot 3/15, rust 13/21, ts 4/23, unity 11/16.

**The reason it is declined is not the rate.** The spread is stack-correlated, which is the
pre-registered "investigate before changing any starter" branch — and the investigation dissolves
it. 19 of the 31 disclosures are about the **live path** (window, keyboard, screenshot), 11 of
those Unity and 7 Rust. Counter-check: agents claiming to have *driven the running application*
number **15 of 23 for TypeScript and 0 of 52 across the other three stacks**, because TS ships to
an automatable browser and Rust/Unity ship a native window the agent cannot type into. The arms
differ in **how much is left to disclose**, not in willingness to disclose it. Re-open only if
the harness gives Rust and Unity agents a way to exercise their own live path.

**Two traps for the next census of this field, both hit here:**

1. `agent.final_text` is the **last** 3000 chars (`wholegame.py:358`), not the first, and not the
   whole thing — 43 of 90 messages are longer. The retired `runner.py:723` kept 1500. Read
   `agent_result.json`'s `.result` instead.
2. `.result` on a quota-aborted trial holds **the API's error string**, not agent text: 9 rows
   are `"You've hit your weekly limit · resets …"` and 6 more are `null`. Anything testing only
   for non-empty will score an error message as a closing report.

**Extraction was pinned before the census**, per rule 12's corollary: the two `wg-g4c` Godot rows
(#98) and the four `wg-arena3d` rows (rule 11) were predicted to disclose from the documents
alone, and all six did.

**The cheaper move this surfaced, not actioned here and not filed as part of this ticket:** the
disclosures exist in 31 of 75 completed trials and **nothing in the grading pipeline reads
them**, which four documents already say to do. Raising a 41% rate that is then ignored is worth
less than reading the 41% already on disk.
