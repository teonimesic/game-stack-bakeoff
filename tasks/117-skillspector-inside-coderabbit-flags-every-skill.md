---
id: 117
title: SkillSpector inside CodeRabbit flags every skill that points at another skill, and this project requires them to
status: done
priority: 4
refs: .coderabbit.yaml, DECISIONS.md Pull requests are reviewed by CodeRabbit, tasks/108, https://github.com/teonimesic/game-stack-bakeoff/pull/2
done_when: PR 2 review 1 has been counted - how many comments carried an AS3 attachment and how many of those were true positives - and either .coderabbit.yaml disables the analyser with that count recorded beside the change, or DECISIONS.md records that attachment-only noise does not meet the reversal condition together with the observation that would
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/4
established_by: 'SkillSpector disabled with the count beside the switch: 14 findings across all rounds, 0 true positives, 0 comments raised by it; the overriding reason is its Prompt for AI Agents block contradicting AGENTS.md. Second defect found and published as FINDINGS 153 - .coderabbit.yaml''s skill path instruction matched 0 tracked files after the skills moved. New gate eval/tools/coderabbit_config.py, --control 5 pins 0 failed, verified here at 0/10 pattern matches. PR #4, 2 review rounds, both comments true positives and both acted on.'
---

On PR 2 (2026-08-23), the first pull request whose diff touched .claude/skills/, every review comment on a SKILL.md carried an attached SkillSpector 2.5.1 warning: [AS3] Skill Enumeration: Skill enumerates or reads other installed skills. Access to other skills SKILL.md files or the skills directory reveals prompt instructions, capabilities, and secrets that should be invisible to peer skills. In this repository that is a false positive by construction. AGENTS.md requires every skill to name its authoritative file and requires the work and dispatch skills to name each other, and the tasks skill to name both. There is nothing to escalate to: there is one operator, one repository, and no peer-skill trust boundary. WHY IT MATTERS. DECISIONS.md records that reviews.tools in .coderabbit.yaml was left deliberately empty in the first version, with a stated reversal condition: the first reviews are the measurement, and if they show noise, disable the tool that produced it and record the review that established it. This is the first evidence against a tool. It is ambiguous evidence and that is the point of the task: SkillSpector produced no standalone review comments, only attachments inside comments that were themselves true positives, so it cost reader attention rather than generating false work. Decide whether that clears the bar. WHAT TO DO. Read PR 2 review 1 on teonimesic/game-stack-bakeoff, count how many of its comments carried an AS3 attachment and how many of those comments were true positives on their own merits, then either add a tools block to .coderabbit.yaml disabling the analyser with that count recorded beside it, or record in DECISIONS.md that attachment-only noise does not meet the reversal condition and what would. Do not change .coderabbit.yaml while a review round is in flight on another branch: it is the configuration under which every other PR is being reviewed.

## note 2026-08-23

**The ticket's premise was wrong, and correcting it is what decided the task.** It said every
review comment on a `SKILL.md` carried a SkillSpector attachment, taken from PR #2's own round-1
adjudication comment. Counted from the API it was **2 of 5**: the 3 comments on `work/SKILL.md`
carried none, because that file names no other skill. The trigger is a **property** — one skill
referencing another skill's file — not the file type, and it is a property `AGENTS.md` mandates.

Counted from `pulls/2/comments` and `pulls/2/reviews`, not from the review prose:

| | |
|---|---|
| review 1 (`5002727074`, head `45ce9d3`) | 8 comments, 5 on a `SKILL.md`, 2 carrying an attachment |
| of those 2, true positives on their own merits | 2, both acted on in `ce4a12c` |
| all 3 rounds | 11 comments, 5 attachments, 0 comments raised *by* SkillSpector |
| findings inside the 5 attachments | 14, of which 0 true positives |
| `[AS3] Skill Enumeration` | 10 of 14 — `dispatch/SKILL.md:10-11`, `tasks/SKILL.md:48-49` |
| `[P7] Indirect Prompt Extraction` | 4 of 14 — the heading `## 6. Improve this skill as you use it`, every time |

**Branch taken: disabled.** `reviews.tools.skillspector.enabled: false`, with the count beside it
in `.coderabbit.yaml` and the derivation in `DECISIONS.md`. The objection the ticket raises —
attachment-only noise generated no false work — is real; what overrode it is that the attachment
ships the remediation *"Remove all code or instructions that list or read other skills' files"*
inside a block headed *"Prompt for AI Agents"*, so an agent in the review loop must re-derive on
every skill PR that this finding contradicts `AGENTS.md`. The schema offers `enabled` and no
per-rule switch.

### What the next agent must not re-derive

- **`skillspector` is a valid key** in `https://storage.googleapis.com/coderabbit_public_assets/schema.v2.json`,
  under `reviews.tools`, documented at v2.5.1 — the same version that produced the attachments.
  Its only property is `enabled`, default `true`.
- **`reviews.tools` does NOT set `additionalProperties: false`.** A typo'd tool key is accepted
  and silently ignored. Nothing gates that, because checking it needs the network.
- **`markdownlint` produced 0 findings and `languagetool` produced 1** across PR #2's 3 rounds:
  `[locale-violation] AFTERWARDS_US` on `dispatch/SKILL.md:134`, which never became a comment.
  1 of 1 decides nothing and it is not wrong by construction. Left enabled.
- **Findings live in 2 channels and only 1 is read by default.** A tool finding appears in the
  review *body*'s tool summary whether or not it becomes a review *comment*. `languagetool`'s
  single finding is body-only. Counting comments alone undercounts what a tool produced.

### A finding, needing a number from the orchestrator

**A path instruction was aimed at an address that no longer existed, and nothing could see it.**
`.coderabbit.yaml` scoped its skill rule to `.claude/skills/**/SKILL.md`. PR #2's *"Keep status
facts in the authoritative document"* comment names `Path instructions` as its source, so the rule
was live and producing true positives. Task 114 then made `.agents/skills/` the single real copy
and left `.claude/skills` a symlink — git tracks it as 1 mode-120000 blob — so the pattern went
from matching the skills to matching **0** tracked files and the rule stopped existing. Nothing
disagreed with anything: a review without a rule looks exactly like a review with it.

Measured, in both directions, before and after:

```
.claude/skills/**/SKILL.md  ->  0 tracked files   red rows: 1   exit 1
.agents/skills/**/SKILL.md  -> 10 tracked files   0 dead        exit 0
```

`AGENTS.md` rule 12. The repair is `eval/tools/coderabbit_config.py`, and the shape of the
finding is that **a documentation move silently disarmed a review rule in a different file** —
the same class as a renamed finding number leaving citations that still resolve.

### The gate, and what it does not cover

`python3 eval/tools/coderabbit_config.py` reds any `path_instruction` covering 0 tracked files,
and reds a config with no path instructions at all. `--control` is 5 pins, 0 failed: green on the
shipped config over its 8 instructions, red on 4 mutants (3 renames each killing a different
address, plus the emptied block).

- **`path_filters` is deliberately out of scope.** An *exclusion* matching nothing is a guard held
  against a future state, and `!eval/runs/**` is one on purpose. Reddening it would fire where
  nothing is wrong.
- **This is not the path check `docstat.py --sweep` deleted.** That one lost because paths in
  *prose* are relative to a context stated in a sentence — 0 true positives, 2 false. A
  `path_instructions[].path` is a glob a machine matches against the repository root.
- **`--root` is the only address input**; the config is derived from it. It took a separate
  `--config` until PR #4's review, which is rule 12 committed inside the gate that enforces
  rule 12.

### Left alone, deliberately

The `AGENTS.md` path instruction matches exactly **1** tracked file while its own text says it
covers *"this file, and the per-directory `AGENTS.md` files"* — of which there are 8, 5 of them
outside `eval/starters/`. Asserting minimatch's treatment of a bare filename would be quoting a
value nobody read. The gate prints the count, so it is visible rather than assumed; settling it
needs a PR touching only `eval/judge/AGENTS.md`.

### Still unestablished

**That disabling SkillSpector stops the attachments.** PR #4 touches no `SKILL.md`, so its 2
reviews carried 0 SkillSpector blocks for the wrong reason. The observation that settles it is the
next pull request whose diff touches a skill: 0 SkillSpector blocks in its review comments. If
they are still there, CodeRabbit reads `reviews.tools` from somewhere this branch did not change.

### Merge ordering

The ticket forbids changing `.coderabbit.yaml` while a review round is in flight on another
branch. Nothing on this branch reaches the reviewer until merge, so the constraint lands on the
**merge**: PR #3 was open with an unreviewed head while this was written.
