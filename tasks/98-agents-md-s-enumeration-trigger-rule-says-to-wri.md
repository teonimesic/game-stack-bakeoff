---
id: 98
title: AGENTS.md's enumeration-trigger rule says to write the trigger as the PROPERTY, and does not say the first property you reach for is usually wrong
status: done
priority: 3
refs: AGENTS.md the rule audit 2026-08-15, tasks/92, DECISIONS.md the census trigger section
done_when: either AGENTS.md states how to choose between candidate properties and cites a measurement, or the omission is recorded as deliberate because the rule is already long enough
established_by: 'AGENTS.md rule audit now states how to choose between candidate properties, with the measurement: a rebuilt QUANTIFIER trigger turns 31 live-corpus lines red with no true positive and gets 12 of 28 shipped pins wrong, while the shipped PREDICATE is at 0 and 0, and the three-wording enumeration it replaced was at 0 false positives. Criterion added: prefer a CLOSED class, decide on the live-corpus false-positive count. Controls both ways on the edited file - docstat.py --sweep exit 0 after the edit, exit 1 with a false census planted in AGENTS.md, restored byte-identical sha256 c52083e85f19. tasks.py check exit 0.'
---

AGENTS.md's most-cited rule is: a rule whose trigger is a list must be re-derived by every reader who meets an item not on the list, so write the trigger as the RESOURCE or the PROPERTY. Every instance it cites is PROSE - a rule in a document. Task 92 is the first time it fired against CODE, a regex, and the repair produced something the rule does not currently say.

There is more than one candidate property, and picking the wrong one is worse than the enumeration you started with. For the aspect-census trigger the obvious property was the QUANTIFIER - a cardinal or all/every governing aspects. Measured over the live corpus it produced 26 red lines, every one a false positive, against an enumeration that produced 0. The property that worked was the PREDICATE - existence, identity or definition - and the reason it worked is stateable: copula, existential there-are and define are CLOSED classes of English, while the phrasings the original enumerated are open.

The candidate addition, one or two sentences, not a new rule: when you replace an enumeration with a property, more than one property fits, and the live-corpus false-positive count is what decides between them. Prefer a property that is a closed class, because that is what makes it not an enumeration in disguise.

Task 92 did not make this edit itself. AGENTS.md is the highest-traffic file here and 7 tasks were in flight; the work skill says to hand a contended file to the orchestrator rather than risk a conflict in a document that states what is true now.

## What was done, 2026-08-23 — do not re-derive any of this

**The edit landed in `AGENTS.md`, in the rule audit, between the "a rule stated as its
instances" paragraph and the closing "state what it protects" line.** One paragraph carrying
the measurement, one block quote carrying the criterion. `DECISIONS.md` was deliberately NOT
touched: its census-trigger section already holds the full derivation, and the new paragraph
cites it rather than restating it.

**The numbers were re-measured, not quoted from this ticket.** The quantifier candidate was
rebuilt from its prose description and run through `docstat.py`'s own downstream census logic,
so both candidates go through identical code and only the trigger differs:

| candidate | red on live corpus | of the 28 shipped pins |
|---|---|---|
| QUANTIFIER — a cardinal or `all`/`every`/`each` governing `aspects` | **31**, none a true positive | **12 wrong** — 6 real censuses missed, 6 correct corpus lines reddened |
| PREDICATE — as shipped | **0** | **0 wrong** |

Corpus at the time: 162 documents swept, **53 live** after `is_archive`. Task 92 measured 26,
this rebuild measures 31 — the same conclusion with a corpus that grew, and 3 of the 31 are
the prose *documenting this very finding*. **Do not read 26 and 31 as a disagreement**; they
are two implementations of one open-class property, and that the count moves with the corpus
is itself the argument for preferring a closed class.

**The rebuild is a reconstruction, not task 92's regex**, which no longer exists in the tree.
The text says so. Anyone re-running it must rebuild it again; there is no shipped producer for
the quantifier count and there should not be.

**Monkeypatching `docstat._ASPECT_CENSUS_RX` works** — `_check_aspect_census` looks the global
up at call time, not at import. Rule 12's fifth row warns about exactly this shape, so the
known-answer control is that the patched run produced 12 wrong pins where the unpatched run
produced 0: if the patch had not taken, both would have read 0.

**Controls in both directions on the edited file.** `docstat.py --sweep` unpiped: **exit 0**
after the edit. A false census appended to `AGENTS.md` — *The five judge aspects are ...* —
gives **exit 1**, and the file was restored byte-identical by a `finally`
(sha256 `c52083e85f19`), with a re-run confirming exit 0. `tasks.py check`: 99 tasks, exit 0.

**What was NOT established.** Whether the closed-class heuristic generalises past this one
trigger. It is stated as a preference with one measured instance behind it, and it says so.
The second instance would be worth recording when a trigger here is next rewritten.

**No finding number was allocated**, deliberately — same reason task 92 gave. Tasks 86, 93, 96
and 97 are all findings-numbering work, and this refines a rule rather than reporting something
that ran and measured nothing. Task 97 is where the task-92 finding lands.
