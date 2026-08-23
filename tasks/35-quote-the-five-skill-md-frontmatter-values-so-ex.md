---
id: 35
title: Quote the five SKILL.md frontmatter values so external tools can parse them
status: open
priority: 2
refs: research/11-doc-linting-for-agents.md, tasks/27
done_when: claude plugin validate --strict over a wrapper containing .claude/skills reports 0 frontmatter errors, and python3 -c yaml.safe_load parses all 7 files; if the quoting turns out to change how Claude Code itself discovers a skill, revert and record that instead
---
## What is this thing?

A **skill** is a procedure this project stores at `.claude/skills/<name>/SKILL.md`. Each begins
with a YAML frontmatter block whose `description` and `when_to_use` fields are the only thing that
decides whether an agent discovers and invokes the skill. `.agents/skills/` holds a second copy of
the same files for Codex (see task 27).

## What is wrong, and how do we know?

Five of the seven `.claude/skills/*/SKILL.md` files have frontmatter that is **not valid YAML**.
An unquoted YAML scalar may not contain a colon followed by a space, and these descriptions do --
for example `description: Add a game task or a play-bot criterion to the eval suite: prompt rules
that ...`.

Measured 2026-08-23 with Anthropic's own canonical validator, `claude plugin validate --strict`
(Claude Code 2.1.220), pointed at a scratch plugin wrapper containing copies of the skills:

    frontmatter: YAML frontmatter failed to parse: YAML Parse error: Unexpected token.
    At runtime this skill loads with empty metadata (all frontmatter fields silently dropped).

Failing: `add-game`, `audit-docs`, `evaluate-run`, `refine`, `run-matrix`.
Clean: `prune`, `tasks` -- their descriptions happen to contain no colon.
The `.agents/skills/` copies fail identically, 5 of 6.

Corroborated by two other parsers: Python's `yaml.safe_load` fails on the same five, and
`vale` 3.18.0 fails **and aborts** -- it refuses to lint the repository at all, returning one
E201 line and nothing else.

Positive control already run: quoting the values in the scratch copy makes all seven validate
clean.

## Why does it matter?

**Claude Code itself tolerates the malformed YAML.** Evidence: a session's available-skills
listing shows every description in full, colons included. So the validator's runtime prediction
does not currently hold for `.claude/skills/`.

What does hold is narrower: **every tool outside Claude Code is locked out of these files**,
including Anthropic's own validator, and the tolerance is undocumented behaviour that can change
in any release. It is also the reason no external linter can be pointed at this repository.

## What should be done?

Wrap the offending values in double quotes, escaping any interior quotes. Five files under
`.claude/skills/` and five under `.agents/skills/`. Nothing else changes.

## Outcomes that count as success

| result | what it means |
|---|---|
| validator reports 0 frontmatter errors and `yaml.safe_load` parses all 7 | done |
| quoting changes how Claude Code discovers or invokes a skill | revert, and record that as the finding -- it would mean the loader depends on the malformed form |

## What NOT to conclude

Do not conclude the skills are currently broken. They load. The defect is portability and the
absence of any external check, not a live failure.
