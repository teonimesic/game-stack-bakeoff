---
id: 89
title: docstat --sweep cannot see a bare flag in a fenced usage block, which is where a phantom flag does most damage
status: done
priority: 3
refs: eval/tools/docstat.py, .claude/skills/audit-docs/SKILL.md
done_when: Either the flag check covers bare flags on fenced command lines with a measured false-positive count on the current corpus and a control in both directions - a planted bare phantom flag reads exit 1, an unmodified corpus reads exit 0 - or the gap is recorded as deliberate in the What it deliberately does not check list in .claude/skills/audit-docs/SKILL.md with the measurement that decided it. Verify by planting a bare phantom flag in a fenced block and reading the unpiped exit code.
established_by: 'Bare fenced-flag check built in eval/tools/docstat.py. Broken state established first: a fenced python3 judge/runner.py --no-such-flag-bare1 read sweep exit 0, the same flag backticked in the same fence read exit 1, clean corpus exit 0. After: exit 1, exit 1, exit 0, all unpiped. Trigger chosen on live-corpus false positives - any bare flag on any fenced line is 8 hits 0 true, widened to prose 2 hits 0 true, shipped trigger 0 hits over a population of 56 fenced lines and 31 in-scope tokens of which 30 resolve to our own argparse. Pinned 6 red and 9 green by _bare_flag_pins() inside --sweep; 4 of 4 mutants caught. One green pin passed for the wrong reason until a mutant found it. Needs a finding number, not allocated here.'
---

Measured under task 77 on 2026-08-23, in eval/judge/JUDGING.md, sweep run unpiped after each plant. The flag check pattern requires backticks. A backticked flag inside a triple-backtick fence IS caught, so there is no fence exemption; a BARE flag on a fenced command line is invisible. Control: the line run judge/runner.py --no-such-flag-ctl3 inside a fence read exit 0, while the same fake flag backticked inside a fence read exit 1. A usage block is normally written bare, and it is the text a reader copies and pastes, so the check misses the highest-damage position while covering inline prose mentions. Widening to bare tokens is not a one-line change: prose em-dash runs and other tools flags would flood it, so it needs its own false-positive count before it is wired in.

## DONE 2026-08-23 - the check was built, not deferred

The gap reproduced independently BEFORE anything was changed, which is what makes the
after-reading evidence rather than agreement: a fenced `python3 judge/runner.py
--no-such-flag-bare1` appended to eval/judge/JUDGING.md read sweep exit 0; the same fake
flag backticked in the same fence read exit 1; the unmodified corpus read exit 0. After
the change those same three read exit 1, exit 1, exit 0.

WHAT WAS BUILT: `_bare_fenced_flags()` in eval/tools/docstat.py. The trigger is a flag on
a FENCED line, occurring AFTER the name of one of this repo's argparse-owning scripts, cut
at the first shell operator. Both halves are derived from the code, never enumerated -
`_our_script_names()` globs eval/ for files containing add_argument, the same glob
`_argparse_flags()` already walks.

THE FALSE-POSITIVE COUNTS THAT DECIDED THE TRIGGER, all over the live 167-document
reference corpus on 2026-08-23:

  any bare flag on any fenced line         8 hits, 0 true positives. git merge --no-ff,
                                           cargo doc --open, Godot --path, vale --config,
                                           npx --yes, the claude CLI's --output-format.
  same trigger over ALL lines, not just    2 hits, 0 true positives. A sentence naming
  fenced ones                              field.py then the claude CLI's --output-format;
                                           one naming a script then git diff --stat.
  SHIPPED: after our script, fenced, cut   0 hits.

THE NUMBER THAT MAKES THAT 0 MEAN ANYTHING, and the one a later reader should not have to
re-derive: the shipped trigger is not quiet because it cannot fire. It reads 56 fenced
lines naming our scripts and 31 in-scope tokens, of which 30 resolve to our own argparse
and 1 is known-foreign. The sweep summary line now PRINTS that population beside the
result, so 0-hits-out-of-32-looked-at can never again read the same as 0-out-of-0.

PINNED BOTH WAYS by `_bare_flag_pins()`, which runs inside --sweep every time and prints
its cases under --selftest: 6 red cases, 9 green. Four mutants were run against the pins
and all four are caught - drop the fence rule, drop the shell-operator cut, delete
backticked spans instead of blanking them, disable the check outright.

TWO THINGS FOUND ALONG THE WAY THAT ARE NOT THE TICKET:

1. A GREEN PIN THAT PASSED FOR THE WRONG REASON, found by a mutant and not by reading. The
   prose out-of-scope pin first read "Pass --no-such-flag-prose to judge/runner.py", with
   the flag BEFORE the script name. The check reads the tail of a line after the script
   name, so that input is invisible whether the fence rule is present or not, and the
   mutant that drops the fence requirement sailed straight through the pin written to
   catch it. Rewritten with the flag after the name, the mutant is caught. The underlying
   property - a flag written before its program is not seen - is correct for a command
   line and is now stated in the docstring rather than left to be rediscovered.

2. --output-format WAS A LATENT FALSE POSITIVE OF THE OLD BACKTICKED HALF, invisible for
   exactly the reason the --wildcards entry beside it already records. It is the claude
   CLI's flag, named in tasks/19 and research/01, and both write it BARE - which the
   backticked half never saw. The first live document to backtick it turned the sweep red.
   Added to FOREIGN_FLAG_PREFIXES with that reasoning written down. A false positive kept
   quiet by the SHAPE of a mention rather than by anything being right is a latent report.

NEEDS A FINDING NUMBER - deliberately not allocated here, per .claude/skills/work/SKILL.md.
The claim: a gate covered the low-damage position (an inline prose mention) and not the
high-damage one (the usage block a reader copies and pastes), and read clean throughout;
and the obvious widening - trigger on the -- token - is the open-class failure AGENTS.md
already records twice, measured here at 8 false positives and 0 true. The closed-class
alternative, "a script this repo owns", is at 0 false positives over a real population
of 31 tokens.

COST: the sweep goes 10.05s -> 10.43s, measured by stashing the change and re-running.
