---
id: 77
title: AGENTS.md says the sweep checks file paths; docstat.py says NO PATH CHECK
status: open
priority: 3
refs: AGENTS.md, eval/tools/docstat.py, .claude/skills/audit-docs/SKILL.md
done_when: AGENTS.md no longer claims a path check that docstat.py does not implement - either the sentence is corrected to name what the sweep actually covers, or the path check is reinstated with the positive control the earlier measurement lacked. Verify by grepping both files and quoting the two lines side by side.
---

AGENTS.md:215 states the mechanical sweep covers 'aspect ids, criterion ids, --flags and file paths across every doc'. eval/tools/docstat.py:1597 reads '# NO PATH CHECK.' and records why it was removed: 0 true positives, 2 false. Both re-read from source 2026-08-23 under task 39. This is failure #38 running backwards: the always-loaded file names a gate that does not exist, so a reader believes the phantom-path class is covered when nothing checks it. It is also one of only two certain contradictions found in a full read of the four always-loaded docs plus all nine skills, which matters because arXiv:2510.14842 identifies conflict between instructions, not their number, as the mechanism behind compliance decay.

## What it turned out to be (2026-08-23, branch task-77-sweep-path-claim)

**The sentence was wrong in two places, not one.** `criterion ids` is also unchecked. The
enumeration named four categories; `--sweep` implements two.

Measured, not read - four plants, each an unfenced line appended to `eval/judge/JUDGING.md`,
sweep run unpiped after each and the file restored:

| planted | exit | means |
|---|---|---|
| a phantom path, `eval/tools/no_such_file_xyz.py` | **0** | no path check |
| two phantom criterion ids, `paddle.telepathy` / `score.rewinds` | **0** | no criterion check |
| a phantom aspect, `feel` / `tuning` | **1** | the tool does read that file at that position |
| a phantom flag, `--no-such-flag-here` next to `judge/runner.py` | **1** | flags are checked |

The last two are why the first two mean absence of a check rather than absence of a reader.

**The sentence was corrected; the path check was NOT reinstated.** Both other refs record its
removal as measured (0 true positives, 2 false), and `audit-docs/SKILL.md` carries an explicit
"Do not fix these by adding them back" list with Paths on it. Reinstating would have
contradicted two documents and a measurement to satisfy one sentence.

**Do not re-derive these:**

- `_criterion_ids()` in `docstat.py` was **defined once and called nowhere** - dead from the
  start. That is what made the claim look backed. Deleted, with the reason left in its place.
- Its extraction was unusable anyway: every `"a.b_c"` string literal in `judge/*.py`, which
  harvests `re.search` and `aspects.py` as criterion ids. If anyone builds a real criterion
  check, the id set has to come from somewhere else.
- `audit-docs/SKILL.md` carried the same phantom (`criterion` in the references row of the
  "asks" table). Fixed there too. The nearby sentence about a flag, path, aspect or criterion
  that does not exist being worse than silence was left alone on purpose: it says why phantom
  names are bad, not what the tool checks, and the same file disclaims paths below it.
- The replacement text does **not** enumerate coverage again. It says the tool defines its own
  coverage and points at it - because an enumeration in prose is exactly what went stale, and
  the 2026-08-15 rule audit in AGENTS.md says to write the property, never the instances.

**No finding number taken.** Seven tasks were in flight, several findings-heavy; the `work`
skill says hand it to the orchestrator rather than race for a number (eleven collisions on
2026-08-23). This is finding-shaped - #38 running backwards - if the orchestrator wants one.

## The write-up turned the gate red, and that was a second defect

Writing the table above made `--sweep` exit 1 on this file: it names a phantom aspect and a
phantom flag as controls, and this file mentions `judge/runner.py`. The aspect check has a
line-scoped exemption for exactly this ("phantom", "plant\w*"); **the flag check had none**,
so no document that mentions our harness could describe a planted phantom flag. A gate that
fails on correct input is a gate that gets disabled - the reason recorded twice already in
`docstat.py`, and the reason the path check was deleted.

Repaired in the same commit: the flag check is now line-scoped and honours the same
exemption, and the vocabulary moved to one module-level constant `_DELIBERATELY_FAKE` shared
with the aspect check, because that list has already drifted once (it held one inflection of
`plant`). Dedup stays per-document; output is now sorted, which it was not - `set()` order
varies between runs under hash randomisation.

Pinned in both directions after the change, in `eval/judge/JUDGING.md`, restored each time:

| control | exit | expected |
|---|---|---|
| phantom flag in prose, no exemption word on the line | **1** | 1 - the check still fires |
| same flag on a line containing "planted" | **0** | 0 - the exemption works |
| same flag **bare** on a fenced command line | **0** | **predicted 1** |
| same flag **backticked** inside a fence | **1** | 1 - no fence exemption |

**The third row is the one that corrected me.** I predicted red and wrote a comment claiming
fenced flags were covered. They are not: the pattern requires backticks, so the check sees
inline code, and a bare flag in a copy-paste usage block - the highest-damage position - is
invisible. That is pre-existing, not introduced here. The comment was rewritten to state the
measurement instead of the prediction, and the gap is **task 89**.
