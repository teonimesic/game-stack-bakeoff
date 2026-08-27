---
id: 183
title: Five argparse dests are read by getattr with a default, so renaming a flag silently changes an arm instead of failing
status: todo
priority: 2
refs: eval/wholegame.py,eval/RUNS.md,eval/PROTOCOL.md
done_when: 'Either the five reads become direct attribute access - `a.harness`, `a.scenes` and so on, so a rename raises AttributeError at the call site - or, where a genuine optional-subcommand case is found, the presence is asserted explicitly rather than defaulted. A control pins it: renaming one flag''s dest must turn something RED. State which of the five, if any, had a real reason for the defensive form, rather than converting all five and assuming none did. A null result closes this - if the loop at line 1282 turns out not to cover a path that reaches these reads, say which path and keep the getattr there with the reason written beside it.'
---

Found by the cleanup pass of 2026-08-27, the first to open the harness.

`eval/wholegame.py` reads five parsed flags through `getattr(a, "<name>", <default>)` rather than `a.<name>`: `scenes` (twice), `harness`, `turn_limit`, `only`, `prompt_file`.

**The defensive form buys nothing here, because the attribute is always present.** The four subcommands that can reach this code - plan, build, evaluate, report - are built in ONE loop at `wholegame.py:1282`, and every flag above is declared inside it, so all four carry all five. The only other subparser, `concurrency-check` at line 1351, dispatches to `cmd_concurrency_check` and never reaches `cmd_build`. So no legitimate call can find the attribute missing.

**What the default CAN do is hide a rename.** `getattr` binds the parser to the code by a STRING, and a string does not fail when the thing it names moves:

| line | read | if the dest ever changes |
|---|---|---|
| 679 | `getattr(a, 'harness', None) or HARNESS` | every trial silently builds with the DEFAULT harness |
| 617 | `getattr(a, 'scenes', None)` | `--scenes` is silently ignored and the run builds no scene |
| 710 | `getattr(a, 'turn_limit', None)` | silently falls back to `MAX_TURNS` |

The first row is the one that matters most. **`eval/RUNS.md` records the harness as an arm dimension**, and a second harness was added on 2026-08-25 specifically so runs could be compared across it. A silent fallback there does not crash and does not warn - it produces a completed run whose recorded arm is wrong, which is the class of defect this project logs as worse than a failure.

Note the shape: this is rule 12 in code rather than in a check. The address is a string, the string is not asserted against the thing it names, and the failure is silent.
