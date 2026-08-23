---
id: 67
title: The TypeScript starter guide is missing a section the other three have
status: open
priority: 3
refs: eval/judge/starter_parity.py agents_md headings, tasks/49
done_when: either the ts guide gains the missing section and starter_parity reports the heading sets equal, or the divergence is recorded as deliberate in the capability register with the reason; and verify_blind, starter_parity and starter_gate_control are re-run
---

## What this is

Each of the four starters ships an `AGENTS.md` — the guide a building agent reads during a trial.
The four are deliberately **not** byte-identical: each is stack-native. But they are meant to
cover the same ground, and `eval/judge/starter_parity.py` measures how far apart they are.

## What is wrong, and how we know

`starter_parity` has collected each guide's **heading set** since it was written, named it in its
own docstring, and compared it with nothing. Task 49 wired the collection to a report — and it
immediately surfaced a forgotten copy.

Measured 2026-08-23:

| section | rust | ts | unity | godot |
|---|---|---|---|---|
| "The one command" | yes | **NO** | yes | yes |

Three guides tell the agent about the one-command contract; the TypeScript guide does not.

("Gameplay is not correctness" was reported by task 49 as missing from unity and is **present in
all four** on re-measurement — that half does not reproduce, and the re-measurement is why this
ticket says so rather than repeating it.)

## Why it matters

This is the **forgotten-copy** shape: four documents maintained in parallel, an edit landing in
three of them, and nothing comparing them. It is the same failure as the deleted skills mirror
(#99) with the copies still live.

The specific cost is one-arm: if the one-command contract is guidance that changes what an agent
does, the TypeScript arm has been running without it, and that is a difference between arms
nobody chose. Whether it *does* change behaviour is unmeasured — say so rather than assuming
either way.

## What should be done

Read the section in the three guides that have it, and decide whether the TypeScript arm's
absence is an oversight or deliberate — the TS toolchain genuinely differs, so "deliberate" is a
real possibility and a legitimate close.

**Either way is a regime boundary if you edit a starter**: `verify_blind.py`,
`starter_parity.py`, `starter_gate_control.py`, and a note in `eval/RUNS.md`. All four gates were
green as of 2026-08-23 and must be re-run.

If the divergence is deliberate, record it where `starter_parity` already reports deliberate
divergence rather than drift — the capability register it prints, which cites `DECISIONS.md`.

## What not to conclude

**Do not make the four guides identical.** `DECISIONS.md` records that they are stack-native by
design, and a parity gate over their prose would fail on correct input, which is how a gate gets
disabled. The question is whether a specific section is missing by accident, not whether the
documents match.
