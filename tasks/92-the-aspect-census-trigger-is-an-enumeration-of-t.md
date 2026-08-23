---
id: 92
title: The aspect-census trigger is an enumeration of the three wordings it was built against
status: open
priority: 3
refs: eval/tools/docstat.py _ASPECT_CENSUS_RX, AGENTS.md the enumeration-as-trigger rule, tasks/79
done_when: either the trigger matches a census claim written in a wording nobody enumerated - proved by planting at least three phrasings not in the current pattern and confirming each goes red - with the false-positive count re-measured over the whole corpus and reported, or the enumeration is recorded as deliberate with the measured false-positive cost of widening it
---

## What this is

Task 79 added `_check_aspect_census` to `docstat.py --sweep`: a live document that makes an
**exhaustive claim** about the judge aspects must name all six within 25 lines. It was built
because two documents said there were five, `--sweep` was exit 0 on both, and the existing
aspect check is structurally blind to that shape — it asks whether a name a document *uses*
resolves, and a document *denying* a judge that exists resolves perfectly.

## What is wrong, and how we know

The trigger is `_ASPECT_CENSUS_RX`, and it is three alternations:

    \w+ aspects (that )?(exist|are defined)      "five aspects that exist"
    these \w+ exist                              "These five exist."
    nothing else is runnable                      RUBRIC's own words

Measured 2026-08-23 by planting census claims in `DECISIONS.md` and running `--sweep` unpiped:

| planted line | fires? |
|---|---|
| `The five judge aspects are architecture, audio, fun, idiomatic and ux.` | **no** |
| `There are five aspects: architecture, audio, fun, idiomatic, ux.` | **no** |
| `the six aspects are listed below` | **no** |

Each is a false claim of exactly the kind the check exists to catch, and each passes.

## Why it matters, and why it is priority 3 rather than 1

`AGENTS.md`'s own audit names this as the most-repeated defect here: **a rule whose trigger is a
list must be re-derived by every reader who meets an item not on the list.** The pattern is the
three wordings that existed on the day it was written.

It is not priority 1 because the check is a real improvement over nothing and both true positives
were caught. The cost is that its coverage is the vocabulary of two documents, and the next
document will be written by someone else.

## What should be done, and the trap in doing it

**Do not simply widen the regex.** Task 79 tried a broader alternative and deleted it before it
ever ran: `aspects.py defines` matched nothing because the docs write it in backticks, and making
it backtick-tolerant fired on `JUDGING.md`'s correct sentence. Its *first* draft fired on three
**correct** lines — sentences describing this very check — which is how the trigger got narrow.

So the widening has to come with **a re-measured false-positive count over the whole corpus**,
the way the current one did (143 docs, 2 red, both true). A trigger that fires on correct input
gets disabled, and this project has three findings recording exactly that.

**Recording the enumeration as deliberate is a legitimate close** — if widening costs more false
positives than the defect costs, say so with the number and stop. That is the same call
`docstat.py` already made when it deleted its path check rather than tuning it quiet.
