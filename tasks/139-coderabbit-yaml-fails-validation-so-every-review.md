---
id: 139
title: .coderabbit.yaml fails validation, so every review since 2026-08-23 ran on default settings
status: done
priority: 1
refs: '.coderabbit.yaml, .agents/skills/work/SKILL.md section 6, .github/workflows/README.md, PR #15 summary comment'
done_when: tone_instructions is within CodeRabbit's 250-character limit with the displaced content moved somewhere that has no limit and the choice recorded; CodeRabbit's summary comment on a fresh pull request no longer carries the parsing-error warning; and a check exists that goes red on an invalid .coderabbit.yaml and green on a valid one, pinned in both directions, so the next over-long field does not repeat this
established_by: 'Closed on evidence, not on the repair. All four done_when clauses hold: tone_instructions is 234 chars against the 250 limit; the displaced checklist is a ''**'' path instruction where the schema''s limit is 20000, with the choice recorded in a comment beside it; and coderabbit_config.py --constraints walks maxLength/enum/type offline against a cached schema, is gated in gates.yml, and FAILS CLOSED when the cache is absent. The control is history rather than a fixture - the real 894-char config restored with ''git show'' is caught by field and by both numbers. The clause that needed a live artifact is now satisfied with a POSITIVE control rather than an absence: PR #20 was reviewed by coderabbitai at 17:52 on 2026-08-24, after the 09:41 repair, producing 16 review threads and ZERO parsing-error warnings. Absence of the warning alone would not have shown this, because a pull request that is never reviewed also carries no warning.'
---

`.coderabbit.yaml` fails validation and CodeRabbit has been reviewing this repository on DEFAULT
settings since 2026-08-23. Measured on PR #15, from CodeRabbit's own summary comment:

    > [!WARNING]
    > ### `.coderabbit.yaml` has a parsing error
    > The CodeRabbit configuration file in this repository has a parsing error and default
    > settings were used instead.
    > Validation error: Too big: expected string to have <=250 characters at "tone_instructions"

`tone_instructions` is **894 characters against a 250 limit, over by 644**. One field fails and the
**whole file** is discarded - the message says default settings, not partial ones.

WHEN: introduced at 894 characters in `7d87e13` (2026-08-23, "Review config and CI docs:
assertive, prose is reviewable, starters are reviewable..."). Every commit of the file before that
has `tone_instructions` absent (0 chars). So every review since 2026-08-23 ran on defaults,
including all of PR #13, #14 and #15.

WHY NOBODY NOTICED, and this is the part worth keeping: **the reviews still looked right.**
CodeRabbit reads `AGENTS.md` by default, so round 1 on PR #15 cited "As per coding guidelines" for
the digits rule and for rule 4 - both of which are in `AGENTS.md` as well as in the dead yaml. A
mechanism that runs, reports success, and measures nothing, whose output is indistinguishable from
the working one. The warning that says so is inside a collapsed `<details>` block in a summary
comment nobody re-reads.

WHAT IS ACTUALLY INERT: everything the yaml adds over the defaults - the path-scoped instructions
(`eval/starters/**`, `.agents/skills/**`, `tasks/**`), the exclusion list, the prose-readability
instructions added 2026-08-23 that `.agents/skills/work/SKILL.md` tells agents to act on, and the
tool toggles. `.agents/skills/work/SKILL.md` section 6 and `.github/workflows/README.md` both
describe behaviour this file is supposed to produce.

NOT FIXED HERE. Shortening `tone_instructions` is a one-line change, but which instructions survive
the 250-character budget is a decision about the instrument that reviews every pull request, and it
should be made deliberately and recorded - the content that does not fit belongs in
`path_instructions` or in `AGENTS.md`, both of which have no such limit.

THE GATE IS THE POINT, not the fix. This failed silently for a day across 3 pull requests, so the
repair is not complete until something turns red on an invalid config: CodeRabbit publishes a JSON
schema and a validation endpoint, and `gates.yml` already runs cheap Python-only checks. Pin it
both directions - a control that goes red on the current 894-character file and green on a valid
one - or the next over-long field does exactly this again.

## note 2026-08-24

## note 2026-08-24 — the config is FIXED; what remains is the gate and the audit

Done already, so do not redo it:

- `tone_instructions` is **234 characters**, under the 250 limit. The displaced checklist moved to
  a `**` path instruction, where the schema's limit is **20000** — recorded in a comment beside it.
- `coderabbit_config.py` gained `constraint_problems()`, which walks `maxLength`, `enum` and
  scalar `type` for every key the schema declares, plus two entry points: `--schema` (network)
  now validates and **caches** the schema, and `--constraints` (offline) reads that cache and
  **fails closed if it is absent**.
- `--constraints` is gated in `gates.yml`, and the register's gate count is 37 with the pin moved.
- **The control is history, not a fixture**: the 894-character config restored from git with
  `git show HEAD:.coderabbit.yaml` is CAUGHT, naming the field and both numbers. A synthetic pin
  would only have proved the walk matches itself.

## What is left for this ticket

The `done_when` clause that is not yet satisfiable: *"CodeRabbit's summary comment on a fresh pull
request no longer carries the parsing-error warning."* That needs a real pull request after this
repair. **Verify it on the artifact, not by reasoning from the diff** — the config is only truly
valid when CodeRabbit says so.

Also open: the walk checks three constraint kinds and deliberately ignores the rest. Decide
whether that is enough, and say why on the property. It is deliberately narrow because a checker
that guesses fires on correct input, which is how a gate gets disabled — but `required`, and
`additionalProperties` where the schema DOES close an object, are candidates with the same
unambiguous character. Choose on the live false-positive count.

## A correction to this ticket's own evidence trail

The orchestrator initially recorded the "default settings" claim as **not established**, having
searched both pull requests' comments with `select(.user.login=="coderabbitai")`. The App's login
is **`coderabbitai[bot]`**, so the filter returned empty for every pull request and the empty set
was read as "no warning exists". Your quotation was correct and complete. The instance is now a
row in AGENTS.md's rule-12 table: verifying someone else's finding is not a safer activity than
making one.
