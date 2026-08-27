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
