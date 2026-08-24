---
name: audit-docs
description: "Audit this project's documentation against reality and against its own rules: the mechanical sweep for names that do not exist, the rule-firing audit, and pruning."
when_to_use: "After a working session; a rule failed to prevent what it was written for; before trusting a document that names code; the docs feel stale. Trigger phrases: audit the docs, are the docs current, why did that rule not fire, check for phantom names."
---

# Auditing the documentation

**Authoritative file: `AGENTS.md` — the rules, the rule audit and the pruning principle. If
this skill and that file disagree, it wins and this skill is the bug.**

The docs are an instrument, and the same question applies to them as to any grader:
*what would it take for this to be wrong?*

## 1. The mechanical sweep — run the tool, do not do this by hand

```
cd eval
python3 tools/docstat.py --sweep      # references + structure; exit 1 if anything fails
python3 tools/docstat.py              # size and token cost of every project doc
python3 tools/docstat.py --outline FILE   # fence-aware heading map
python3 tools/docstat.py --renumbered # citations of a finding number that has moved
python3 tools/docstat.py --withdrawn  # live docs restating a figure declared retired
python3 tools/docstat.py --citations  # a census, never a gate: hashed numbers naming no finding
python3 tools/withdrawn_control.py    # its controls; --mutate NAME to see them go red
python3 tools/fragment_control.py     # the integrity check's controls; --mutate NAME, --list-mutants
python3 tools/integrity_census.py     # how often the debris has ever occurred; --windows, --control
python3 tools/linkcheck.py            # every relative link in the live docs: path AND fragment
python3 tools/linkcheck.py --selftest # its controls, three link shapes, both directions
```

`--sweep` asks three kinds of question:

| | asks | bought with |
|---|---|---|
| **references** | does a harness flag or an aspect id a doc names actually exist? | `RUBRIC.md` named five judges that do not exist (#38) |
| **structure** | does a file parse as the thing it is read as? | 5 of 7 skills had frontmatter no YAML parser could read; `AGENTS.md` rules 10-16 detached from their own list |
| **integrity** | is the text itself intact, or did an edit leave debris behind? | an edit rewrote a wrapped sentence in `eval/FINDINGS.md` and left its last line stranded at line 6, where every session is told to read first; a rewrite applied to half of one `DECISIONS.md` bullet left the old text beside the new, eight lines apart |

**The integrity question is the one no consistency check can ask.** Debris left by a botched
edit states nothing, so it disagrees with nothing — it is damage rather than a wrong claim, and
it survived precisely because every other gate here looks for disagreement. The trigger is
*repetition*, which is a closed property of the text rather than a vocabulary. Both halves run
over the **archive as well as the live docs**, which the formatting gates do not, because one
of the two instances was in the archive and debris is not evidence.

**There are two halves and they do not substitute for each other — the gap between them is
measured, not assumed.**

| | asks | its one real instance |
|---|---|---|
| stranded tail | does a whole LINE recur in the paragraph above it? | `eval/FINDINGS.md:6` at `1f6fb65` |
| duplicate fragment | does any 12-word WINDOW recur inside one paragraph, list item or frontmatter key? | `DECISIONS.md:745` at `75dde71` |

**Both measure 0 at HEAD, and that is not a reason to retire either.** The tree at any one commit
holds only the defects nobody has repaired yet, and both of these were repaired — so 0 is what a
census of HEAD must return whether the gate is protecting or dead. The population that can tell
those apart is every *revision* of every reference document:

```
python3 tools/integrity_census.py     # 1 incident each over every version in history
```

It runs both checks' known-answer pins first and refuses to print a census if either fails, and
it asserts that every reference document tracked at HEAD appears in its historical enumeration —
prove the extraction, and the *population*, on a row whose true value you can state in advance.
That second control exists because the first enumeration was 22% short and said nothing: `git log
--name-only` omits a merge commit's file list, and one tracked skill was added by a merge. It is a
census, never a gate — everything it can find was repaired before it existed.

The second was added because the first scores **0** on the `DECISIONS.md` defect: the duplicated
span begins mid-sentence and ends mid-sentence, so no line of it and no sentence of it recurs
whole. An exact-match rule over repeated sentences scores 0 there *and* 0 on the live corpus —
the obvious property, and a complete false negative.

**The window is a free parameter and it was chosen on the live false-positive count**, never on
which size sounds more principled. Window 10 gives 3 corpus hits, 11 and up give 0, and the real
defect is invisible from 16. All 3 hits at 10 are the same *antithesis* — `DECISIONS.md`'s
headroom blockquote repeating a clause to carry an argument — which is the shape this check will
keep meeting, because correct prose repeats itself. 12 ships rather than 11 to keep a word of
margin at each end.

**If you retune it, re-measure over the corpus as it stands then, with the producer:**

```
python3 tools/integrity_census.py --windows   # hits AND distinct phrases, per window
```

**Read the distinct-phrase column, not the hit count.** At 183 documents window 10 gave 1 hit; at
188 it gives 3, and the two extra are that same antithesis quoted in `DECISIONS.md` and
`tasks/119` *because* it was named as the false positive that set the boundary. A trigger that
fires on a passage correct documents quote grows its own count by being written about, and
reading that as an open class would argue for widening a window that has not moved.

`tools/fragment_control.py` prints the corpus count at the **shipped** window only — 0 — which is
not the number that decides a retune. Its 8 mutants each flip a row that names them.

**`--sweep` deliberately does not check file paths, and `linkcheck.py` is what covers the gap
for links** — a phantom `eval/RUBRIC.md` passed a green sweep. It resolves the path *and* the
GitHub heading fragment, so a reworded heading turns a citation red instead of leaving a link
that still resolves and points at nothing. It does not check bare paths in prose; only links.

**`--renumbered` asks the third kind, and it is the one the other two cannot ask: does a
name still mean what its author meant?** When two worktrees allocate the same finding number
the merge renumbers one of them, and every document that already cited it now points at a
stranger *while still resolving* — so nothing above can see it. It derives the map of moved
numbers from git history, resolves each citation against the numbering its own authoring
commit saw, and prints two lists: **decided** (a verdict, and the half `--sweep` echoes) and
**undecidable** (a short list to read, because a merge writes the renumber and the citation
in one commit and there is no ordering inside a commit). 27 stale citations across eight
corpora on first run, plus two more that landed while it was being written (#118).

Never renumber a finding to satisfy it. The number in `eval/findings/` is the published one;
the citation is what is wrong.

**The undecidable half is a standing list, so read only what it prints as `UNTRIAGED`.** The
verdicts already reached are in `eval/renumber_triage.json`, keyed by the citing text — task 102
read all 51 rows, repaired 15 and recorded 36. When you adjudicate a fresh row, add the entry;
`--sweep` gates on an entry whose sentence no longer exists, and `tools/triage_control.py` is
its 14 controls. **Every one of the 15 that were wrong was a task citing the number it had
allocated itself** — the author's own worktree numbering was never committed, so history has no
answer, and the row you should suspect first is a `tasks/` file talking about its own finding.

**`--withdrawn` asks the fourth kind: is a figure that was RETIRED still stated as current?**
No consistency check can ask this. When a stale figure propagates, the copies **agree** — with
each other and with the original, to the digit — so propagation and consistency are the same
observation, and the figure-agreement check built for exactly this found 52 figures, one
disagreement, and that one a false positive (#113). What separates a live figure from a retired
one is only whether a withdrawal was **declared**, which is a fact about the record.

So it is declared, in `eval/withdrawn.json`, and the rule has no vocabulary in it: if every
`match` pattern of an entry occurs inside one block of a **live** document and that block does
not contain the entry's **id**, it is a live restatement. **When you withdraw something, add the
entry and then repair what the check names.** When a live document legitimately needs to state a
retired figure — a withdrawal notice, a historical paragraph — put the id in that block:

```
... was **withdrawn** — FINDINGS #113, register entry `WR-tier3-pair`.
```

The id, never a marker word. `withdrawn`/`superseded`/`retracted` is an enumeration, and the
aspect check below already failed on one inflection of one verb. The archive
(`eval/findings/`, `eval/FINDINGS.md`, both `IMPROVEMENTS.md`, `CLEANUP-LOG.md`, `tasks/`) is
out of scope entirely — see `DECISIONS.md` for the partition and why it is written down.

**`--citations` asks what all four gates above assume: does a cited number name any finding at
all? It is a CENSUS that exits 0 — not a fifth gate.** Every check above is about a number that
*exists*, so a fabricated `(#999)` planted in a live document reads exit 0 from all of them
(#146). The obvious widening was measured before anyone built it, and it is not built: `#`
before a number is a rule number, a task id, a table row, a GitHub issue and *"the #1 risk"* as
well as a finding citation, so the trigger fires on correct prose. Run it when you are auditing
citations and want the candidates in front of you, and **read the rows rather than counting
them** — the total is dominated by correct English, and at the last adjudication every row was.
It prints its population, the range it compared against and the producer of that range, because
the figure it replaces was published with none of the three and did not reproduce the same day.

**The references half reads the skills too, including this one** — since 2026-08-23 (task
44). It did not before: the corpus was built with `glob`, `glob` does not descend into
dot-directories, and every skill lives under one, so for the whole life of the sweep the
always-loaded instruction documents were the only files it could not see. Measured when
they were let in: **0 false positives**, after fenced lines stopped counting as claims.

Prose is executed by a person, and **a person does not get an argparse error**. A file
naming a flag, path, aspect or criterion that does not exist is worse than one that says
nothing: it is confidently wrong and it will be followed.

The structure half exists because eleven documentation linters were measured against this
repository and produced **over 14,000 alerts and two defects, both structural**
(`research/11-doc-linting-for-agents.md`). Do not add a prose linter; that survey already
came out.

### Do not hand-roll it

Four hand-written versions were wrong before the tool existed, each in a way whose output
looked like a real finding:

| attempt | failure |
|---|---|
| fence-blind heading scan | reported a GDScript `##` doc-comment inside a ``` block as a malformed heading |
| first sweep | 73 hits, ~65 false — `--max-turns` is the claude CLI's, not our argparse |
| narrowed sweep | 2 hits, both false; the path check had **0** true positives |
| aspect check | went silent under a planted phantom — a file-wide exemption let one legitimate "candidate" sentence silence every check in that file |

The last one matters most: the sweep read **clean**, and clean-because-nothing-is-wrong
was indistinguishable from clean-because-it-cannot-fire. Only the planted-phantom control
separated them.

### If you change the tool, re-run both controls

Or you have not changed it — you have replaced it with something that agrees with you:

```
# negative: clean corpus -> exit 0
python3 tools/docstat.py --sweep

# positive: plant a phantom aspect -> exit 1
# A PRIVATE address. A fixed name under the system temp directory is one
# every concurrent session can write, and the restore below writes back into
# the REPOSITORY - so two audit passes at once restore each other's copy,
# and one of them may still carry a planted phantom. mktemp cannot collide.
BAK=$(mktemp) || exit 1
cp judge/JUDGING.md "$BAK"
printf '\nIf `feel` and `tuning` rank alike they are one judge.\n' >> judge/JUDGING.md
python3 tools/docstat.py --sweep ; echo "expect exit 1"
cp "$BAK" judge/JUDGING.md

# positive: plant a fake FLAG -> exit 1, and its exemption -> exit 0.
# Both halves, or you have shown only that the check can fail, not that it can still pass.
# The trailing `# phantom` exempts THIS line; the sentence it plants carries no exemption
# word, which is the whole point - a control that plants a self-exempting line tests nothing.
printf '\nPass `--no-such-flag-x` to judge/runner.py.\n' >> judge/JUDGING.md  # phantom
python3 tools/docstat.py --sweep ; echo "expect exit 1"
cp "$BAK" judge/JUDGING.md
printf '\nWe planted `--no-such-flag-x` next to judge/runner.py.\n' >> judge/JUDGING.md  # phantom
python3 tools/docstat.py --sweep ; echo "expect exit 0 - the planted line exempts itself"
cp "$BAK" judge/JUDGING.md

# positive: a BARE phantom flag on a FENCED command line -> exit 1. This is the half that
# did not exist before task 89, and the one a reader copies and pastes. Its green partner
# is the line below it: real flags of ours, written bare in the same position.
printf '\n```\npython3 judge/runner.py --no-such-flag-bare1\n```\n' >> judge/JUDGING.md  # phantom
python3 tools/docstat.py --sweep ; echo "expect exit 1"
cp "$BAK" judge/JUDGING.md
printf '\n```\npython3 judge/runner.py --run-dir runs/x --rounds 3\n```\n' >> judge/JUDGING.md
python3 tools/docstat.py --sweep ; echo "expect exit 0 - both flags resolve"
cp "$BAK" judge/JUDGING.md

# positive: unquote a skill description so it contains ": " -> exit 1
# positive: append "10. x", a 4-space line, a blank, then a 3-space line -> exit 1

# the withdrawal register's own controls, including a planted retired figure and the
# real tree at 25fe630 where it really was published in three live documents
python3 tools/withdrawn_control.py                  # 54 controls, expect exit 0
python3 tools/withdrawn_control.py --mutate any_of  # expect the named control to FAIL
python3 tools/withdrawn_control.py --list-mutants
```

**Plant the phantom in prose, never inside a ``` fence** — for the **aspect** check a fenced
line is not read as a claim (see below), so a control planted in a code block goes green and
tests nothing. The `printf` above appends an unfenced sentence for exactly that reason.

**The flag check does not share that rule, and knowing which you are controlling matters.**
It has no fence exemption, and it is now **two halves with different triggers**:

| half | trigger | corpus measurement |
|---|---|---|
| backticked | `` `--<flag>` `` anywhere, in a doc that names one of our harnesses | 0 hits |
| bare (task 89) | a `--<flag>` on a **fenced** line, after the name of one of our argparse-owning scripts, before the first shell operator | 0 hits over 56 such lines and 31 in-scope tokens, of which 30 resolve to our argparse and 1 is known-foreign |

Until 2026-08-23 only the first existed, so a **bare** flag on a fenced command line — the
ordinary way a usage block is written, and the text a reader copies and pastes — was the
one position nothing looked at. The plant that established it: a fenced
`python3 judge/runner.py --no-such-flag-bare1` read exit 0 while the same fake flag
backticked in the same fence read exit 1.

**The trigger is the script name, not the `--` token, and that was decided on a count.**
Scanning any bare flag on any fenced line finds **8 hits on the live corpus and 0 true
positives** — `git merge --no-ff`, `cargo doc --open`, `Godot --path`, `vale --config`,
`npx --yes`, the claude CLI's `--output-format`. Every one another tool's flag. Widening
the same trigger to unfenced prose costs **2 false positives and 0 true**. This is the
closed-class rule in `AGENTS.md`: a `--` token is an open class, a script this repo owns
is not.

The bare half is pinned in both directions by `--selftest`, and **the green pins are the
half that matters** — a pipe handing the line to `grep --color`, a backticked script name
with a bare flag, and the prose case that is out of scope on purpose.

Both structure checks arrived on an **already-repaired** repository, which is the state in
which a gate has never been seen to fail. Plant the defect each names before trusting it.

### What it deliberately does not check

Do not "fix" these by adding them back. Each was measured and removed:

- **Paths.** Docs legitimately write them relative to a context stated in prose or a table
  cell: `README.md` named `tools/boundary.gd` in a row about `template-godot/`, where it
  existed (that row is gone with the tree, #122; the example stands as the reason).
  Measured 0 true positives, 2 false. A check that cannot be made reliable is
  removed, not tuned until it is quiet — tuning until quiet is how a check comes to pass
  vacuously.
- **Criterion ids.** Never implemented, though `AGENTS.md` and this file both claimed it
  until 2026-08-23 (task 77) and a `_criterion_ids()` helper sat unused in `docstat.py`
  making the claim look backed. Two phantom ids planted in prose read exit 0. The helper is
  deleted; **if you build this, the id set cannot come from string literals in `judge/*.py`
  — that pattern harvests `re.search` and `aspects.py` as criterion ids**, and a check whose
  corpus is junk goes quiet rather than wrong, which is the harder failure to see.
- **Foreign flags.** `--max-turns`, `--permission-mode` belong to the claude CLI.
- **A bare flag in unfenced PROSE, and a bare flag on a fenced line that names no script
  of ours.** Both were built and measured on 2026-08-23 (task 89). Prose: 2 false
  positives, 0 true — a sentence naming `field.py` and then the claude CLI's
  `--output-format`, and one naming a script and then `git diff --stat`. Prose backticks
  its flags, so the other half already has those. Fenced lines owning no script of ours:
  8 false positives, 0 true, all another tool's flags. **A bare flag written BEFORE the
  program it belongs to is also unseen**, which is correct for a command line and is
  recorded because a mutant found it, not a reader.
- **`code` and `look` as aspect ids.** Ordinary words that appear as inline code for other
  reasons.
- **`findings/`.** An archive whose subject matter is naming superseded things.
- **Anything inside a ``` fence, for the aspect check.** A fenced line is a command to run
  or an output to expect; it asserts nothing about its own arguments. This is what let the
  skills into the corpus: the only aspect hit across all 124 documents was the `printf`
  above, in this file, planting `feel` and `tuning` as the sweep's own positive control.
  The exemption is **line-scoped** — a file-wide one once let a single legitimate
  disclaimer silence every aspect check in its file, and the control went green.
- **A bare `aspect`-headed table, for the census check.** A table listing five of the six
  ids with no exhaustiveness claim in prose above it goes unreported. The structural
  trigger was written and measured at **9 false positives** on live docs (task 92, #140) — every
  one a legitimate per-aspect *results* table over the subset a round actually ran. The
  census check reads the sentence, so **write the claim above the table or it is unguarded.**
- **Any wording that counts aspects without asserting what the set IS.** `All five aspects
  were run`, `six aspects x 5 repeats`, `which aspects are included` are true sentences and
  stay green. The trigger asks for an existence, identity or definition predicate with the
  list adjacent — three separate quantifier-based drafts were measured at 26, 31 and 27
  false positives and **0 true positives each** (#140).
- **Root blocks indented 1-3 spaces, in general.** The indent check asks only about a
  continuation under a **2+ digit** ordered marker, which is the only form with a true
  positive here. The broad form fires on `tasks/` files where nothing is wrong — 2-space
  lists and prose introduced by a colon, with no list item above them. A gate that fails
  on correct input gets disabled.
- **`eval/findings/`, `eval/FINDINGS.md`, `eval/RUNS.md` for structure.** The archive
  records what was true when it was written, including broken shapes it is about;
  reformatting one to satisfy a gate edits evidence.

## 2. The rule audit

For each rule: **has it ever fired?** *Fired* means it changed what happened, not that it
was read. Of those that fired, did they fire correctly?

- **Fired and was wrong as written** → rewrite it. Several rules here were violated by the
  person who had just written them; that is evidence about the rule, not the author.
- **Never fired** → is it preventing failures silently, or dead weight? Those look
  identical from outside. The test: can you construct a plausible situation where it
  would fire? If yes, keep it.
- **Fired and was ignored** → it is in the wrong place, or buried under rules that do not
  earn their space.

**The commonest defect is a trigger written in the vocabulary of the incident that
produced it.** "Do not run judge or LLM calls during the build" missed *subagent* — it
named mechanisms when what mattered was the resource. State what the rule protects, not
what went wrong last time. A trigger that is a list must be re-derived by every reader who
meets an item not on it.

## 3. Prune

Every rule that does not earn its place makes the ones that do harder to find. A document
nobody finishes reading protects nothing. When a rule is superseded, **replace** it.

Two exceptions, both about numbers rather than rules:

- A **published figure later proven wrong** stays marked, because someone may have acted
  on it.
- A **superseded reading of evidence** stays marked where the reading was published — the
  numbers were right, the inference was not, and deleting it hides that the inference
  moved.

## 4. What is a doc and what is a skill

- **Skill** — a procedure with a start and an end, invoked when you are doing that thing.
- **Doc** — what is true: evidence logs, ledgers, contracts, decisions.
- **Always-loaded rules** — constraints belong in `AGENTS.md`, never a skill. A constraint
  you have to remember to invoke is a constraint that will fail.

A skill that restates a doc creates two sources of truth. Every skill here names its
authoritative file and says explicitly: if they disagree, the doc wins and the skill is
the bug.

## The test

Not whether the documentation is thorough. **Whether the next session makes new mistakes
instead of these ones.**
