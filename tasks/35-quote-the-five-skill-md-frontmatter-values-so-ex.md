---
established_by: 'Quoting only; no field''s text changed. claude plugin validate --strict (Claude Code 2.1.220) over a scratch plugin wrapper: HEAD gave 5 frontmatter errors and exit 1, fixed gives Validation passed and exit 0. PyYAML 6.0.3: 5 of 7 .claude/skills SKILL.md failed with ScannerError before, 7 of 7 parse after; the two that already passed, prune and tasks, are byte-identical to HEAD. Every rewritten line was asserted to round-trip, so the parsed value equals the raw text that stood after the key before, byte for byte; bodies and the name and argument-hint keys are unchanged. Claude Code discovery is NOT changed, checked as the task required: a headless run in the worktree enumerated its available-skills listing and all seven appear with full description and when_to_use verbatim, colons intact, so no revert. The 5 .agents/skills Codex copies had byte-identical frontmatter and got the same fix, 10 files total, commit d8157fa on task-35-quote-frontmatter. Repo-wide sweep of all 51 tracked files with frontmatter: the only remaining failures are 21 tasks/*.md, filed as task 40 because quoting those alone would break tasks.py, which parses with a regex and writes back unquoted - demonstrated on task 06. tasks.py check still exits 0 with 40 tasks all well-formed.'
id: 35
title: Quote the five SKILL.md frontmatter values so external tools can parse them
status: done
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
