# Does instruction count predict rule compliance?

**Task 39.** Design written 2026-08-23, before any trial was run. `pool.py` and `run.py` are
the apparatus; **this file is the design, and if the two disagree the design wins and the code
is the bug.**

## The question

`AGENTS.md` and its three folder-scoped siblings are loaded on every turn of every session in
this repository. arXiv:2509.21051 (*When Instructions Multiply*, 2025-09-25) reports that
instruction-following compliance falls as the number of simultaneously-active instructions
rises, across 10 models, and that **a logistic regression on instruction count alone predicts
compliance to about 10% error**. Its two benchmarks reach **10 instructions** (ManyIFEval,
text) and **6** (StyleMBPP, code).

So: how many instructions does this project load, and does compliance fall at that number?

## What is already established, before any spend

### 1. The always-loaded set holds 73–113 instructions

`eval/tools/instruction_census.py`, run 2026-08-23 against the main checkout and against this
branch, which agree to the digit:

| doc | lines | ~tokens | strict | broad | blocks |
|---|---|---|---|---|---|
| `AGENTS.md` | 531 | 8702 | 39 | 60 | 52 |
| `eval/AGENTS.md` | 216 | 3353 | 20 | 30 | 22 |
| `eval/judge/AGENTS.md` | 179 | 2978 | 12 | 20 | 16 |
| `research/AGENTS.md` | 43 | 686 | 2 | 3 | 3 |
| **total** | **969** | **15719** | **73** | **113** | **93** |

Three definitions are reported, not one, because *how many instructions are in a document* has
no ground truth and a single keyword list is exactly the enumeration failure the rule audit in
`AGENTS.md` warns about. `--selftest` pins the counter in both directions: it goes up on
normative fixture prose, returns **zero** on declarative prose whose fenced block is stuffed
with the marker words, and it asserts its own known miss — a bare imperative whose verb is not
on the list.

**This repository sits at 7–11× the right-hand edge of the only measured curve.** Every
statement anyone makes about compliance here, including the vendor line that longer files
"reduce adherence", is an extrapolation beyond the data.

### 2. The always-loaded set contradicts itself in at least two places, verified against code

arXiv:2510.14842 identifies **conflict between instructions**, not their number, as the
mechanism behind compliance decay. Conflict is measurable with no run at all. Two, re-read from
source rather than from the scan that proposed them:

- `AGENTS.md:215` states the mechanical sweep covers "aspect ids, criterion ids, `--flags` and
  **file paths** across every doc". `eval/tools/docstat.py:1597` reads **`# NO PATH CHECK.`**,
  and gives the measurement that removed it: 0 true positives, 2 false. A reader who trusts the
  always-loaded file believes a class of defect is gated when it is not.
- `.claude/skills/evaluate-run/SKILL.md:59` states "the five aspects that exist";
  `eval/judge/aspects.py:281` defines **six** (`IDIOMATIC, ARCHITECTURE, FUN, FUN_FRAMES, AUDIO,
  UX`). This is failure #38 — a doc naming judges that do not exist — running in reverse.

Filed as **tasks 77 and 79**; they are recorded here because they bear on the design. **The
experiment must not be run on a conflicting pool**, or it measures 2510.14842's mechanism while
claiming to measure 2509.21051's.

## The design

### The subject and the manipulation

One base task, held **byte-identical** in every arm: write a single-file Python script that
summarises a `cost_usd` key across the JSON files in a directory. The only thing that moves is
how many pool instructions are attached to it.

| arm | k | trials | obs/instruction |
|---|---|---|---|
| `k1` | 1 | 32 | 2 |
| `k2` | 2 | 16 | 2 |
| `k4` | 4 | 8 | 2 |
| `k8` | 8 | 8 | 4 |
| `k16` | 16 | 8 | 8 |
| `k1pad` | 1 | 32 | 2 |

**Trials per arm are deliberately unequal.** A trial yields *k* observations, so equal trials
per arm gives radically unequal observations per instruction. The first `plan` run, at 12 per
arm, left **four instructions with zero observations in the `k1` arm** — a content difference
that would have been read as a count effect. `plan` exits non-zero on any zero and is the gate
against it.

### The control arm, and why the experiment is worthless without it

`k1pad` carries **one** instruction in a prompt padded to the token length of a `k16` prompt.

Instruction count and prompt length rise together. Length alone is known to degrade behaviour
(arXiv:2402.14848; Chroma's context-rot measurements). A decline from `k1` to `k16` therefore
changes two things at once, and reading it as a count effect is `AGENTS.md` rule 8 — *the
comparison that is available, cheap, and produces a conclusion indistinguishable from a clean
one*.

The padding is drawn from the project's own always-loaded documents and filtered through
`instruction_census.classify`, keeping only sentences the census scores as **non-normative**. The
control and the census therefore agree by construction rather than by promise: the padding adds
tokens and, by the same instrument that produced the count above, no instructions.

| outcome | reading |
|---|---|
| `k1pad` ≈ `k1`, `k16` < `k1` | the effect is **count** |
| `k1pad` ≈ `k16` < `k1` | the effect is **length**; count is not shown to act |
| all three equal | no measurable effect at this n — a result, and it closes the ticket |

#### The padding filter, and the two leaks that built it

`run.py padcheck` is the control on this arm, and it fired twice on real leaks before it
came out clean. Both were found by **rendering the actual prompt and reading it**, not by
reasoning about the filter:

- the first rendered `k1pad` prompt contained *"Label unverified claims as unverified. An
  unlabelled guess is indistinguishable from a measured fact"* — an instruction, and
  specifically the source rule behind pool instruction **F2**. `classify` missed it because it
  decides a bare imperative from an enumeration of verbs and `label` is not on it;
- with that fixed, the next contained *"The fallback turns an error into a plausible in-range
  number"* — word for word the source rule behind **B1**.

The fix for the first was not to add `label` to the verb list; that is re-deriving the
enumeration the rule audit warns about. The filter now enumerates what to **accept** —
`SAFE_OPENERS`, plus no emphasis, no backticks, no clause-boundary punctuation — and drops
everything else. **The two lists fail in opposite directions on purpose:** a miss in the census
costs the count, a miss here costs only padding volume.

`padcheck` verifies the survivors by two mechanisms rather than one threshold, because a
control that shares its subject's assumptions is the #37 shape: a 5-gram overlap test (which
can catch a regression in the filter's 4-gram rule) and a pool-identifier scan (which can fire
on a paraphrase no shared word-run would reveal). It also asserts the filter still admits
enough prose to pad with — measured in **characters against the required volume**, because an
empty accept-list satisfies every safety property here and would silently turn `k1pad` into
`k1`. An earlier version asserted a *sentence count*, which is a proxy for the quantity that
matters and is #59's failure in miniature.

**The residual limitation, stated rather than hidden.** The padding is drawn from a corpus
that is *about* rules, so it cannot be guaranteed free of normative flavour, only of anything
the census scores as an instruction, anything opening as an imperative, and anything restating
a pool instruction. **If residual instructions remain, they inflate `k1pad`'s effective
count** — which makes the control conservative for a *count* claim and liberal for a *length*
claim. So a result of `k1pad ≈ k1` is trustworthy; a result of `k1pad ≈ k16` must not be read
as "the effect is length" without saying that the padding may itself carry instructions.

### The estimand: within instruction, never between

The primary comparison is **the same instruction at k=1 against itself at k=16**, paired,
with the 16 paired differences tested by an exact two-sided sign test and a bootstrap CI over
instructions.

This is the whole answer to the ticket's third pre-registered outcome — *the experiment cannot
be designed without confounding instruction count with instruction content*. It can, and this is
how: **content is held constant by construction, because both members of every pair are the same
sentence.** Which instructions accompany it is randomised; order within the block is shuffled
independently and recorded, because order is a separate measured variable (arXiv:2402.08939)
and this design balances it rather than testing it.

### The compliance measure

Per (trial, instruction) **binary**, decided by a deterministic checker. No model grades
anything: an LLM judge would put the instrument being measured inside the measurement.

Explicitly **not** a readability score, and not any whole-document metric. §4.6 of
`research/11-doc-linting-for-agents.md` established that nothing connects those to
instruction-following in either direction, and adopting one would be #59's proxy failure with
prose in place of `ux`.

### The pool

16 instructions in `pool.py`, each drawn from a rule this project's own documentation states,
each restated only as far as needed to make it checkable on this artifact, with the original
quoted in `Instruction.source`. Two classes, reported separately because pooling across a
population not shown to be homogeneous is rule 4:

- **F1–F6, format** — an ISO date in the docstring; an `UNVERIFIED:` line; citing
  `eval/IMPROVEMENTS.md` by path and never bare; ≤88-column lines; no tabs; the
  `raise SystemExit(main())` guard.
- **B1–B10, behavioural** — no error-swallowing `except`; atomic write via `os.replace`; `n`
  beside the mean; `source_dir` recorded; annotated `main`; loud non-zero exit on a missing
  directory; refusing to overwrite an existing output; naming unparseable files in `errors`;
  an audit trail in `files_read`; silence on stdout.

Seven are checked by **running** the artifact against a fixture tree, in three separate working
directories — the happy path, a directory that does not exist, and a run over an output file
that is already there. Two instructions concern paths the happy case never touches, and a
checker that only ever sees the happy path cannot see either.

### Controls on the instrument, all offline

`python3 eval/instrfollow/pool.py --selftest`, green as of 2026-08-23:

| control | asks | result |
|---|---|---|
| **positive** | can the checks go green at all, and are the 16 mutually satisfiable? | gold artifact, **16/16** |
| **negative** | can each check fail, and does it fail *alone*? | 16 mutants, **each flips exactly one** |
| **variant** | can each check still **pass** on a legitimately different artifact? | **16/16** |
| **fail-closed** | is anything credited to a non-artifact? | unparseable source, **0/16** |

The negative sweep's second half is the half that matters. Requiring each mutant to flip
**exactly one** checker is what establishes that a compliance count over this pool counts
sixteen things rather than one thing counted sixteen times — rule 9 pointed at the instrument
before it is pointed at the result. It has already earned its place twice:

- the `F1` mutant replaced an ISO date with a longer phrase and pushed the line past 88
  characters, flipping `F4` as collateral;
- two format checkers credited **2/16** to a source file reading `def main( :`, because short
  tab-free text satisfies them. That is a fail-**open** channel (rule 7), and the parse gate now
  zeroes everything. A *runtime* crash deliberately does not zero the format checks: the file is
  still readable Python, and `usable` carries the distinction for the analysis to partition on.

An earlier draft carried a seventeenth instruction, *the file must have a module docstring*. It
was removed: three other instructions check that docstring's **contents**, so it could not be
observed independently of them, and non-independent observations are not what a count is over.

### What would make this measure nothing

Pre-registered, because a mechanism that runs, reports success and measures nothing is the
single pattern behind most findings in this repository.

- **Saturation.** If every checker passes at every k, the manipulation is inert and the answer
  is *no measurable relationship, effect bounded by the interval at this n* — which closes the
  ticket. `analyse` flags every instruction with zero variance by name and refuses to hide it
  in a pooled rate. An inert term is a question about the quantity, not the parameter (rule 16).
- **Uniformity across instructions.** If all 16 move identically, that is the signature of a
  shared cause, and the shared cause is usually the instrument (rule 9).
- **A binding turn ceiling.** `--max-turns 40` is a ceiling that may bind; `analyse` reports the
  max against it and says so. Per rule 8's qualifier, a ceiling is raised rather than held.
- **No budget cap is passed.** A budget flag is visible to the callee and is therefore an
  instruction (#33) — and this experiment counts instructions.

### Arm is confounded with time, and what limits it

Trials run **sequentially, arm by arm**, so the order in which arms were measured is also
the order in which they were run: every `k1` trial precedes every `k16` trial. Rule 10 says
to partition by anything about the world that changed while a run was in flight, and here a
drift in the API's behaviour over the run would be indistinguishable from a count effect.

**`k1pad` bounds it, and does so without any extra spend.** It carries the same *k*=1 as the
first arm and runs **last**, after `k16`. So if `k1` and `k1pad` agree, nothing that varies
with wall-clock moved compliance across the run — the arm built to control for prompt length
turns out to control for elapsed time as well, because it is the only arm that repeats an
earlier arm's *k* at the far end of the schedule.

This is worth stating as a limit rather than a feature: it bounds drift, it does not
eliminate it, and a within-arm interleaved schedule would be strictly better if this is ever
re-run.

### Isolation

Every trial runs in a fresh directory **outside the repository**, with
`--setting-sources project`. Outside deliberately: this project's own `AGENTS.md` would
otherwise add its 73–113 instructions to *every* arm and swamp a manipulation whose largest arm
is 16. `--allowedTools Write Edit Read`, no Bash — the base task says not to run the script, so
a shell would only add a variable and a denial stream.

## The pilot, and what it changed

An 8-trial pilot ran first, at **$0.83 measured**. It was not a smoke test: it changed the
apparatus twice, and both changes were invisible to the offline control suite.

**1. One fixture made the behavioural checkers dependent on each other.** The fixture tree
held an unparseable `bad.json`, so every artifact *not* given B8 — *name the files that would
not parse* — crashed on it, and B3, B4, B9, B10 and `usable` all failed as collateral. Three of
the five pilot artifacts read `usable=False` for that reason alone.

This is invisible to a mutant sweep by construction: every mutant is derived from the gold
artifact, which already obeys all sixteen. It is rule 15 exactly — *a mutant asks whether a
check can fail; only a variant asks whether it can still pass* — and the input that exposed it
was not adversarial at all. It was the ordinary, reasonable output of an agent that was never
given B8. **The variant fixture I had written shared the gold's assumptions and could not have
found it.**

The fix runs the artifact in **four** working directories rather than three, and B8 is now the
only checker that reads the malformed one. Verified in both directions against the stored pilot
artifacts: the three that read `usable=False` read `True` after, the one that was already
`True` was unchanged, and no check flipped in the wrong direction.

**2. One instruction was ambiguous, and the ambiguity looked like non-compliance.** B9 said
*"the list of files actually read"*, and a pilot artifact listed only the files it took a value
*from* — a defensible reading. Ambiguous wording produces variance that is about the wording
and not about the count, and this design cannot tell those apart. The wording was tightened;
**the checker was not loosened**, because loosening it would have hidden the ambiguity instead
of removing it.

## Cost

Measured, not projected — `eval/AGENTS.md` forbids extrapolating across a boundary that has not
been measured across. Pilot: **$0.83 / 8 trials**, ranging $0.054 (k1) to $0.322 (k16); cost
rises with k, so a pooled per-trial mean would misprice any arm. The full-run figure is recorded
in `RESULT.md` beside the numbers it paid for.

## What must not be concluded

Taken from the ticket, and repeated here because this file is what a later reader will find:

- **A null does not make `AGENTS.md` useless.** Every rule in it was bought with a real
  incident; an unmeasured benefit is not an absent one.
- **A positive result does not mean the file should be shorter.** Count and content move
  together unless the design separates them; this design separates them *within the pool*, and
  says nothing about whether removing any particular rule would help.
- **Neither result transfers to the folder-scoped or starter files** without measuring them.
