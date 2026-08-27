---
id: 185
title: capability.py's TRIAL_RE does not match a scene trial, so the scene submission is stack '?' and invisible to the four-arm gate
status: done
priority: 3
refs: eval/judge/capability.py,eval/SCENES.md
done_when: a scene trial id parses to its game and its stack, so wg-scene-s1ts-2026-08-25/s1_parallax__ts__t0 reports under 'ts' rather than '?' - or the module states in code that the four-arm gate is asked of game submissions only and reports how many records it excluded, so a reader can see the population. Either way a control that hands the sweep a scene record and asserts which population it lands in, red before green.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/61
established_by: 'Merged as PR #61. capability.TRIAL_RE was ^(g\d+_[a-z0-9]+)__([a-z]+)__t(\d+)$, so of 69 stored records exactly 1 failed to match - s1_parallax__ts__t0 - and parse_trial returned (''?'',''?''). The report printed a ? row of n=1 beside the four arms in all 9 field tables and still printed ''GATE: no stack-correlated gap in any declared field''. THE AGENT DID BOTH BRANCHES OF THE TICKET''S ''or'' AND WAS RIGHT TO: parsing without partitioning pools a scene into the ts arm''s min/median/max, and narrowing without parsing leaves the record in a ? row nothing reads. Verified by the orchestrator on the branch: s1_parallax__ts__t0 now parses to (''s1_parallax'',''ts''), a junk id still returns (''?'',''?''), and the report prints ''69 stored submissions (68 game, 1 scene)'' with ''GATE POPULATION: the four-arm gate is asked of the 68 game submissions (arms godot, rust, ts, unity); 1 scene record excluded (arms ts)''. That last line is the generalisable repair and the agent named it as such: not ''widen the pattern'' but ''a gate prints the population it asked and what it left out''. A FACT THE ? ROW WAS HIDING: capture.cpu_seconds and capture.peak_rss_mb are populated on the scene record and on 0 of 68 game records, because rusage capture landed after every game run and before the scene run - uniform within each (run, class) cell so not a gate failure, but previously visible only as a ? row nobody read. Controls red before green: against the pre-fix module the new controls give 4 explicit FAILs plus an AttributeError at exit 1; after, all hold at exit 0, with 4 mutants and 4 variants including a single-arm scene run beside a full game matrix staying GREEN. One thing checked rather than assumed: sweep() keys a run by the first path part under --runs, which would pool a wrapper''s inner run directories - proved on a known-good row first, 0 of 69 records disagree. Filed rather than fixed: tasks/188, for 3 outside-diff review comments on DECISIONS.md lines written by tasks 171 and 167 and pulled into the review''s file set by the main merge, one of which claims a contradiction inside rally.counts''s own definition and needs bot_pong.py read beside the paragraph. Findings #201.'
---

capability.TRIAL_RE is ^(g\d+_[a-z0-9]+)__([a-z]+)__t(\d+)$, so the one stored scene submission, wg-scene-s1ts-2026-08-25/s1_parallax__ts__t0, parses as game '?' stack '?'. It is a ts submission. Every per-stack partition in the module therefore excludes it: the distribution tables print a '?' row of n=1 beside the four arms, and no_stack_correlated_gap and stack_skew_warnings both filter on ARMS, so its fields are never asked the question the gate exists to ask. The gate still reports 'no stack-correlated gap' - it is not wrong, it is answering over 68 of the 69 records without saying so. It found nothing today because the scene's fields are all populated; a scene submission with a genuine per-arm absence would be silently uncounted. Found while doing tasks/182, which left it alone as out of scope.

## note 2026-08-27

Done in PR #61, branch `task-185-capability-scene-population`. Both branches of the
`done_when` are implemented, because each alone leaves the other defect standing:
parsing the id without partitioning pools a scene into the `ts` arm's min/median/max,
and narrowing the gate without parsing leaves the record in a `?` row nothing reads.

## The broken state, established before the fix

Over the 69 stored `eval/programmatic.json` records, exactly 1 fails
`^(g\d+_[a-z0-9]+)__([a-z]+)__t(\d+)$` - `s1_parallax__ts__t0` - and `parse_trial`
returned `('?', '?')` for it. The report printed a `?` row of `n=1` beside the four arms
in all 9 field tables and still printed `GATE: no stack-correlated gap in any declared
field`.

## What it looks like now

    69 stored submissions (68 game, 1 scene)
    GATE POPULATION: the four-arm gate is asked of the 68 'game' submissions
      (arms ['godot', 'rust', 'ts', 'unity']); 1 'scene' record excluded (arms ['ts'])
    GATE: no stack-correlated gap in any declared field

## A fact the `?` row was hiding, which nobody should re-derive

`capture.cpu_seconds` and `capture.peak_rss_mb` are populated on the scene record and on
**0 of 68** game records. rusage capture landed after every stored game run and before
the scene run. It is uniform within each `(run, class)` cell so it is
`not_captured_in_this_run` and NOT a gate failure - but the only place that date
boundary was visible before this change was a `?` row a reader would skip.

## Design decisions a future session should not re-open blind

- **`GATE_TASK_CLASS = "game"` narrows exactly one question**: are all four arms present?
  Four arms is a property of the game matrix; the scene class has been built on 1 arm, so
  demanding four of it goes red on the state of the corpus rather than on a defect.
- **Excluded is not unread.** The unexplained-null check runs over every record whatever
  its class, a record whose class the module cannot name is itself a gate failure, and
  every per-arm comparison happens inside one `(run, task class)` cell. That last one is
  what makes a scene gap findable: with a mixed run pooled by run alone, the godot arm
  looks populated by its GAME records and the scene gap is invisible. The mutant for it
  is in the selftest.
- **The class is taken from `aspects.task_class`, not decoded from the regex.** One
  answer to *what class is this task*, 3-valued, consulting the suites before the id
  shape. The control states `"scene"` as a literal rather than calling the same function,
  because a control that imports its expectation from its subject is not a control.

## Checked and found sound, so it does not need re-deriving

`sweep()` keys a record's run by the first path part under `--runs`, which would pool a
wrapper's inner run directories. Proved the extraction on a known-good row first
(`wg-scene-s1ts-2026-08-25` must map to itself): **0 of 69** records have a top-level
part differing from their run directory, and the gate returns 0 problems under either
key. Nothing to repair.

## FOR THE ORCHESTRATOR: this needs a finding number

I did not allocate one, per `.agents/skills/work/SKILL.md` §2. The claim:

> A filter written before a population existed excludes that population silently, and
> reports clean. `capability.TRIAL_RE` was written when every task was a game. When the
> scene class arrived, its one submission parsed to game `?` stack `?`; every per-stack
> partition dropped it, `no_stack_correlated_gap` and `stack_skew_warnings` both filter
> on `ARMS` so its fields were never asked the question the gate exists to ask, and the
> gate reported "no stack-correlated gap" over 68 of 69 records without saying so. It
> found nothing because the scene's fields happened to be populated; a scene submission
> with a genuine per-arm absence would have been uncounted.

The generalisation, and the reason it is worth a number rather than a line: **this is the
enumeration failure of `AGENTS.md`'s own rule audit, in a regex rather than a sentence,
and it fails SILENTLY on the population that did not exist yet.** A wrong answer would
have been loud. What it produced instead was a correct answer over a population it did
not name. The repair that generalises is not "widen the pattern" - it is that a gate
prints the population it asked and the records it left out, so a narrowing is visible
without anyone having to suspect it.

## Review

3 rounds on PR #61. Round 1: one Minor on `DECISIONS.md` - the paragraph was a log of a
past defect, and its "68 of 69" contradicted the "all 68 stored submissions" four lines
above. Acted on: the paragraph states the rule, the same criticism was applied to two
`capability.py` comments the reviewer had not flagged, and the corpus figure is stated
once with its producer and the date it was read. Round 2: one Minor, the module
docstring still stating a 68-record corpus; the number was removed rather than
resynchronised, because a second unproduced corpus figure goes stale forever. One `68`
is kept and now reads as dated provenance - "the corpus as it stood on 2026-08-23 - 68
submissions, all of them games" - which is checkable, the only scene run being dated
2026-08-25. Round 3, after merging `main`: 3 outside-diff comments, all on prose from
tasks 171 and 167 that arrived with the merge. Declined here and filed as `tasks/188`
with the authoring commits named; one of the three is a claimed contradiction inside
`rally.counts`'s own definition and needs `judge/bot_pong.py` read beside the paragraph,
which is a different repair from a wording fix.

Nothing in this branch's own diff drew a comment in any round.
