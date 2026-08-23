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

## What was done, 2026-08-23 — do not re-derive any of this

**The defect was worse than this ticket states.** Planting 14 census claims, each false in the
way the check exists to catch, the old trigger fired on **2**. The ticket's three are a subset;
the other nine that passed include *the full list of aspects is X*, *the complete set of aspects
is X*, *each of the five aspects - X - is judged*, and *aspects.py defines five: X*.

**The obvious repair is not merely imperfect — it is 100% false positives. Measure it before
spending any time on it.** A trigger built on the QUANTIFIER (a cardinal, or `all`/`every`/`each`
governing `aspects`) caught 10 of the 14 and turned **26 correct live-corpus lines red, with no
true positive among them**. In this corpus a counted plural `aspects` overwhelmingly describes
what *ran*, *cost* or *failed*: `All five aspects were run over a full eight-submission field`
(`DECISIONS.md`), `All five aspects failed their gates` (`eval/G4-PLATFORMER.md`), `ALL SIX
aspects separate g4_platformer at n=5` and `six aspects x 5 repeats` (`eval/judge/JUDGING.md`,
`eval/RUNS.md`). Adding a *must name at least one id nearby* precondition only cut 26 to 15.

**What worked is the PREDICATE.** A census asserts existence, identity or definition, in the
present tense, with the enumeration adjacent; a run description does not. `were run`, `failed`,
`separate`, `x 5 repeats` are none of those. It is statable as a property rather than a wordlist
because copula, existential *there are*, and *define*/*list*/*set* are **closed classes of
English**, unlike the open class of verb phrases the original enumerated. One extra
discriminator was needed and is pinned: a restrictive or interrogative determiner (`which
aspects are included:`, heading `JUDGING.md`'s table of pooling subsets) narrows the set and
never declares it. That was the single false positive the predicate trigger produced before
`_CENSUS_NOTREL` was added.

**Measured after the change.** 14 of 15 plants red. **0 red across the 152-document swept
corpus.** Widened to all 2090 markdown files in the checkout: 6 red, all 6 inside `tasks/` or
`eval/findings/` and therefore archive-exempt, and all 6 true statements of a superseded census.
The three phrasings in the table above were re-verified end to end — planted into `DECISIONS.md`
with `--sweep` run unpiped: old trigger **exit 0** on all three, new trigger **exit 1** on all
three, `DECISIONS.md` restored byte-identical by a `finally`.

**Deliberately still not covered, with its price.** A bare `aspect`-headed table listing five ids
with no claim in prose above it. The structural trigger for it was written and measured at **9
false positives** on live docs (`JUDGING.md` 361, 467, 547, 612, 662, 799, 1279,
`G4-PLATFORMER.md:301`, `DECISIONS.md:651`) — every one a legitimate per-aspect *results* table
over the subset one round actually ran. Recorded in `DECISIONS.md` and in `audit-docs/SKILL.md`'s
list of what `--sweep` does not do, with the instruction that follows from it: **write the claim
above the table, or the table is unguarded.**

**Two things worth knowing before touching this again.**

1. **The widened check's first live firing was on the `DECISIONS.md` paragraph documenting it.**
   That paragraph quoted two false censuses as examples and `--sweep` went red on it. The check
   was working. The declared way to show a census you do not mean is a ``` fence, which is
   already a pinned green — so the fence in that paragraph is load-bearing, not decoration.
2. **A concurrent agent was planting a census control into `eval/judge/RUBRIC.md` while this was
   being measured**, and the corpus-wide probe caught it mid-flight as an apparent live-doc false
   positive that vanished on re-run. Repeat any corpus census here, or read it against
   `git status`, before believing a single hit.

**Pins went from 10 to 28** in `_aspect_census_pins`: 15 red, 13 green. The 13 greens are the
half that matters — every one is real corpus text that some draft of this trigger turned red.

**No finding number was allocated, deliberately.** Tasks 86, 91, 93 and 96 are all
findings-numbering work with several in flight, and eleven finding-number collisions happened on
this date. Filed as **task 97** with the numbers ready to land. **Task 98** was filed for the
`AGENTS.md` rule this refines: the enumeration-as-trigger rule says to write the trigger as the
property, and does not say that more than one property fits or that the first one you reach for
may be 100% false positives. `AGENTS.md` itself was left unedited on purpose — highest-traffic
file here, 7 tasks in flight.
