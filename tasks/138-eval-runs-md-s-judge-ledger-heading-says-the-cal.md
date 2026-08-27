---
id: 138
title: 'eval/RUNS.md''s judge-ledger heading says the calls spend money, which is the claim #159 exists to retire'
status: in_review
priority: 3
refs: 'eval/RUNS.md, #159, eval/tools/tokenvalue.py, eval/tools/docstat.py, tasks/128, tasks/130'
done_when: 'The heading no longer claims the calls spend money, and every anchor or link that pointed at it still resolves (`linkcheck.py` exit 0, checked BEFORE and AFTER so the anchor move is observed rather than assumed). Plus a decision, recorded either way: whether any gate can cover a prose expenditure claim - chosen on a measured live-corpus false-positive count, with ''no trigger beats the corpus, so none was added'' being a complete and preferred answer over an open-class word list.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/62
---

`eval/RUNS.md` heads its specialist-judge ledger *"Specialist-judge calls — a separate ledger,
because they spend money too"*. **They do not spend money.** Every `$` figure this project produces
is `tokval`, a list-price valuation of tokens on a subscription account, and no figure here is an
expenditure (#159). The heading asserts the exact thing task 128 spent a whole ticket removing,
directly above a table of the figures it mislabels.

Spotted by the agent working task 130, three lines above its diff, and deliberately left alone
there: changing a heading moves an anchor, and this belongs to the #159 clean-up rather than to a
figure decision.

## Why the existing gate did not catch it

`docstat.py --money` looks for a money **sigil** — `$` next to a digit. This heading has no digit
in it: the claim is carried by the verb *"spend"*, in prose. So the gate is not broken and does not
need loosening; it is answering a narrower question than the one #159 raises.

That is the interesting half of this ticket. **A word-based trigger is an open class**, and this
project has measured what that costs: an independently rebuilt quantifier trigger landed on 31
red lines with no true positive among them, while the closed-class predicate it replaced sits at
0 false positives (AGENTS.md, the census-trigger section). So do NOT reach for a list of
expenditure verbs. If a check is worth adding, choose it on the live-corpus false-positive count
and say what the count was; if no trigger beats the corpus, fixing the heading and recording that
no gate covers prose claims is a complete answer.

`tokenvalue.py --selftest` already pins "no expenditure word in the unit" and "no expenditure word
in a formatted figure" — check whether the population those run over can be widened to headings
before writing anything new.

## note 2026-08-27

The heading now reads *"Specialist-judge calls — a separate ledger, because they consume account
capacity too"*. `eval/AGENTS.md` already names that resource, so the heading and the guidance
agree.

## The anchor move was observed, not assumed

`linkcheck.py` exit 0 before **and** after, over its 4 live documents. The move itself was read
out of `linkcheck.github_anchor`, the checker's own derivation:

- old `specialist-judge-calls--a-separate-ledger-because-they-spend-money-too`
- new `specialist-judge-calls--a-separate-ledger-because-they-consume-account-capacity-too`

**0 tracked files reference either anchor**, over every path `git ls-files` names — so no link
into `eval/RUNS.md` broke, and that is a measurement rather than an inference. `eval/RUNS.md` is
not in `linkcheck.LIVE_DOCS`, so the default run never covered it either way.

## The gate question is settled: no trigger was added

The candidates were run over `docstat._live_corpus` and `_claim_blocks` — the gate's own
population and window, 57 live documents:

| candidate | red blocks | after the repairs |
|---|---|---|
| closed-class predicate alone, `$` dropped | 76 | 71 |
| predicate **and** a closed-class money noun (`money`/`dollar`/`cash`), no `$` | 13 | 5 |
| shipped: predicate **and** a `$` figure | 0 | 0 |

**8 of the narrow candidate's 13 were this project's own resource in the retired vocabulary and
are repaired.** Re-running it over the repaired corpus is what decides the gate: **5 red, 0 true
positives.** 2 are `DECISIONS.md` explaining the money gate and denying the figures are real,
which `#159` exempts by design; 3 are correct prose about somebody else's money — GitHub's
billed Actions minutes, `--max-budget-usd` as its vendor documents it, and published
eval-methodology advice about API spend, 2 of them in `research/`, whose `AGENTS.md` requires a
sourced claim.

**The distinguishing property is WHOSE money, and a possessor is not a closed class of English.**
Both halves of the trigger are closed classes and it does not help. Recorded in `DECISIONS.md`
under *A prose expenditure claim carries no figure and is NOT gated — decided 2026-08-27*, with
what re-opens it: re-run the narrow candidate and read it against the 5 recorded there.

The ticket asked whether `tokenvalue.py --selftest`'s population could be widened to headings.
**It cannot usefully**: its 2 expenditure-word pins run over `UNIT` and a formatted figure —
module constants, not documents — and widening them to prose puts a second markdown corpus scan
beside `--money`'s. The trigger is what fails, not the population. Same entry.

## What the next agent must not re-derive

- The 8 repaired lines and their wording are tabulated in the pull request body (#62).
- **The recorded counts move when the repairs are reworded, and both review rounds moved them.**
  The predicate-alone figure went 73 → 71 when round 1 removed two more predicate words. It was
  re-measured each time rather than adjusted. Anyone editing that entry's prose must re-run the
  candidate and reconcile the table, or the entry becomes a stale count with a producer.
- **`eval/RUNS.md:217` carries a broken shortcut reference** — `[#46]` used in prose with no
  definition, so it renders as literal text. `linkcheck.py eval/RUNS.md` exits 1 on it, before
  and after this work. Pre-existing, unrelated to this ticket, and **no gate covers it** because
  `eval/RUNS.md` is not in `linkcheck.LIVE_DOCS`. Left alone deliberately; worth a ticket of its
  own, together with whether `LIVE_DOCS` should include `eval/RUNS.md`.
- **A finding may be worth allocating** and the orchestrator owns the number: *the money-unit
  gate requires a `$` beside its predicate, so 8 live lines asserted the retired claim in prose
  beside it — one of them a section heading directly above the table it mislabelled — and
  widening the trigger cannot be done, because the property that separates our tokval from
  somebody else's money is the possessor, which is not a closed class.*
- Two self-inflicted instances of rules this project already has, recorded so they are not
  repeated. `skill_layout_control.py` was launched twice concurrently; the two runs stomped each
  other's plant and left `.claude/skills` as a real directory instead of the symlink. It was
  restored from `HEAD` and a single clean run then read 5/5. The *"it exited 0 while printing
  FAILED"* reading of the bad run was `head`'s exit status through a pipe (rule 3), not the
  tool's — `cmd_run` returns `1 if bad else 0` correctly. **Run `skill_layout_control.py` one
  instance at a time, and unpiped.**
- The review took 3 rounds and cost more than that in requests: the org's CodeRabbit allowance
  was exhausted when the pull request opened, and `pr_review_state.py` answered
  `LANDED_COMMENT ... notice=Review limit reached` at exit 0 — a landing verdict on a head no
  round had read. `--ignore-notice` does not help, because the stop is on the summary comment,
  not on the notice. **Read the `notice=` field, not only the verdict.**
