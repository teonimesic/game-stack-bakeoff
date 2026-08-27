---
id: 183
title: Five argparse dests are read by getattr with a default, so renaming a flag silently changes an arm instead of failing
status: done
priority: 2
refs: eval/wholegame.py,eval/RUNS.md,eval/PROTOCOL.md
done_when: 'Either the five reads become direct attribute access - `a.harness`, `a.scenes` and so on, so a rename raises AttributeError at the call site - or, where a genuine optional-subcommand case is found, the presence is asserted explicitly rather than defaulted. A control pins it: renaming one flag''s dest must turn something RED. State which of the five, if any, had a real reason for the defensive form, rather than converting all five and assuming none did. A null result closes this - if the loop at line 1282 turns out not to cover a path that reaches these reads, say which path and keep the getattr there with the reason written beside it.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/53
established_by: 'Merged as PR #53. All five getattr(a, ...) reads are now direct attribute access, and the ticket''s null branch was CHECKED rather than assumed: git log -S on each read reaches only the commit that introduced the flag, and a3d0fd1 already had the single-subparser-loop shape, so none of the five ever had a real reason for the defensive form. concurrency-check reads four flags of its own and none of the five, and nothing outside main() builds a Namespace and calls a cmd_* function. ''or HARNESS'' at the harness site was dead for the same reason and went too - the flag declares default=HARNESS with choices, so the parser cannot produce a falsy value. Verified by the orchestrator on the branch: 0 getattr(a, ...) reads remain, flag_binding_control.py exits 0 at 14/14 rows as declared, and I drove the defect back myself - restoring the pre-183 getattr form at both select_tasks call sites turns flag_binding.py RED at exit 1 naming ''cmd_build:617 getattr()'', with the repaired tree green. The control is layered for a measured reason: BIND reads the command functions as an AST and would have been GREEN on the historical state, because with a dest renamed AND getattr restored the read is gone from the AST entirely - only BY-STRING reddens, and it fails on the whole closed class getattr/setattr/hasattr/delattr/vars rather than on an enumeration. Two incidental findings the agent recorded: the SELFTEST row was red on first run and right to be, because -h carries dest=''help'' with default=SUPPRESS so deriving dests from action.dest alone over-reports; and naming wholegame.py in .github/workflows/README.md reddens docstat --selftest''s recorded-exclusion pin, so the added paragraph says ''the whole-game harness''. NO FINDING NUMBER, and the agent''s reasoning for declining one is right: no dest has ever been renamed in this repository''s history, so this closes a latent defect rather than correcting a result, and there is no candidate event to audit the stored manifests against.'
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

## note 2026-08-27

Done on branch `task-183-flag-dest-binding`, PR #53. All 6 reads are now direct attribute
access; no `getattr` on the namespace survives anywhere in `eval/wholegame.py`.

**None of the five had a real reason for the defensive form.** Checked rather than assumed:

- All four subcommands reaching these reads (`plan`, `build`, `evaluate`, `report`) are built
  in one subparser loop and all five flags are declared inside it. `git log -S` on each read
  reaches only the commit that introduced the flag - `a3d0fd1` for `turn_limit`, `only`,
  `prompt_file`; `51719c9` for `scenes`; `44fba4e` for `harness` - and `a3d0fd1` already had
  the single-loop shape. There was never a subcommand carrying some of them and not others.
- `concurrency-check` dispatches to `cmd_concurrency_check`, which reads `k`, `submission`,
  `starter`, `game` and none of the five.
- Nothing outside `main()` builds a `Namespace` and calls a `cmd_*` function. The one
  namespace-passing call in the repository is `return cmd_report(a)` at the end of
  `cmd_evaluate`, and it passes the namespace `main()` produced.

So the null branch of `done_when` does not apply, and `or HARNESS` at the harness site was
dead for the same reason as its `getattr`: the flag declares `default=HARNESS` and
`choices=sorted(agent_harness.HARNESSES)`, so the parser cannot produce a falsy value.

**What the next agent should not re-derive:**

- `main()` is now `build_parser()` + module-level `DISPATCH` + `DELEGATES_TO`. `DELEGATES_TO`
  exists because a read inside a delegate must bind under the CALLER's subparser; it is
  checked against the AST call graph, so adding a delegation without declaring it goes red.
- `eval/tools/flag_binding.py` is the gate (13 rows), `flag_binding_control.py` the pin
  (14 rows: PRISTINE, 6 MUTANT, 2 VARIANT, 2 DISARMED, 3 BEHAVIOUR). Both run in `gates.yml`.
- **Its SELFTEST row was red on first run and was right to be.** `-h` carries `dest="help"`
  with `default=SUPPRESS`, so argparse never puts it on the namespace; deriving dests from
  `action.dest` alone over-reports by exactly that name. The derivation filters on both.
- **`BIND` alone would not have caught the historical state.** With the dest renamed AND the
  `getattr` restored, the read has vanished from the AST, so `BIND` is green and only
  `BY-STRING` reddens. That is why `BY-STRING` fails on the whole closed class
  `getattr`/`setattr`/`hasattr`/`delattr`/`vars` rather than on a default argument.
- The three BEHAVIOUR rows are the measurement, on the real module: unrenamed `cmd_plan`
  returns 0; with `--scenes`' dest moved on the parser action it raises
  `AttributeError: 'Namespace' object has no attribute 'scenes'`; with
  `getattr(a, "scenes", None)` restored the same rename returns 0 and raises nothing.
- `gates.yml`'s pinned gate count moved 53 -> 55 (`ci_minutes.py --selftest` and the two
  places `.github/workflows/README.md` states it). `ci_minutes --controls` reads 36 of 40.
- **Naming `wholegame.py` in `.github/workflows/README.md` reddens `docstat --selftest`'s
  recorded-exclusion pin**, which asserts the CI register names no harness script. The added
  paragraph says "the whole-game harness" instead. Worth knowing before the next register edit.

**Not established, and stated as plainly:** no run under `eval/runs/` was affected. No dest
has ever been renamed in this repository's history, so this closes a latent defect rather
than correcting a stored result - there is no candidate event to audit the stored manifests
against. Nothing here was proposed as a numbered finding on that basis.
