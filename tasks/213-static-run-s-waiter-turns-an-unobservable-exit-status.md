---
id: 213
title: static.run's waiter turns an unobservable exit status into exit 0 - the one fail-open fallback in the tier-1 measurement path
status: done
priority: 5
refs: eval/judge/static.py, eval/judge/rusage_selftest.py
done_when: 'a fixture that forces os.wait4 to raise (ChildProcessError, in-process, the way this ticket''s probe did) takes static.run over a command whose true exit is nonzero and gets back NOT exit 0 - the module''s existing convention for an unspawnable binary (code 127) with a note in `note` that names the HARNESS as the cause ("could not reap: ..."), streams preserved, peak_rss_mb and cpu_seconds None (the honest third value, not 0.0) - pinned red-first in eval/judge/rusage_selftest.py (whose subject is already what static.run observes) with the unforced control still reading the true exit; the spawn-failure path keeps its 127 and the timeout path keeps its 124-with-note, both asserted unchanged in the same check; python3 eval/judge/rusage_selftest.py exits 0 unpiped after, and python3 eval/judge/capture_selftest.py is unaffected (it drives static.run over real children on every check).'
established_by: 'PR #92 squash 2a4328c, branch head f8dc5d9e65d50617a864f9202ad2f94622037d7c; verified at f8dc5d9 in own detached checkout unpiped: rusage_selftest exit 0 (38 PASS, 0 FAIL) with reap fixture + control + spawn/timeout variants + automated mutant all run and read, independent orchestrator probe (forced wait4 -> 127 + could-not-reap note + None resources; control reads 3; pure-timeout note byte-identical), capture_selftest and runner_capture_selftest exit 0, sweep exit 0; review LANDED_COMMENT zero inline threads at that head; merge head gates+controls green (gates 3m8s, controls 16m48s); no finding allocated (the defect is the ticket itself, filed by the ninth cleanup pass with the forced-wait4 probe before the fix); merged main gates green unpiped (sweep, renumbered, tasks.py check).'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/92
---

`eval/judge/static.py`'s `run()` waits on the child with a waiter thread calling
`os.wait4(p.pid, 0)`. Its failure branch is:

    except (ChildProcessError, OSError):
        reaped.put((0, None))

Status 0 means "exited 0" to everything downstream. `code = 124 if timed_out else
p.returncode` then reads 0, and `build.compiles`, `verify.green`, `lint.clean` and
`tests.green` - the criteria that GATE - would each record `exit 0` from a command
whose status was never observed, with empty streams and no note. This is AGENTS.md
rule 3's sibling verbatim: *never write `cmd || echo 0` on anything you will read as a
measurement - the fallback turns an error into a plausible in-range number, which is
the most dangerous shape a broken check can take.* It is the only `put` of a fabricated
status in the module, and it sits in the one function every tier-1 command goes through.

**Reachable today? No, and that is why this is p5.** `wait4` fails only on a child that
was already reaped or an unexpected OSError; the module suppresses Popen's own waitpid
precisely so the two cannot race, and nothing else reaps `p.pid`. The channel is
latent in the same sense as tasks/211: one future change - a diagnostic `p.wait()`, a
concurrent `collect` sharing pids, a platform quirk in `wait4` - makes it real, and the
direction it fails is a GREEN GATE with no evidence, not a crash. The authors defended
the Popen side of this exact race (the comment on `p.returncode`) and left the wait4
side fail-open.

**What NOT to conclude:** nothing stored is wrong. Every stored grading was produced
by a `wait4` that returned. This is the channel, not a wrong number - the same split
tasks/211 drew. Do not touch published figures; do not write into `eval/runs/`.

**Model for the fix:** the module's own spawn-failure branch, three lines up. A binary
that could not be spawned returns code 127 with `note=f"could not run: {ex}"` - fail-
closed, named cause, and `rusage_selftest.py` already pins it. The reap-failure branch
should read the same way: a sentinel status (not 0), decoded as 127 with a note naming
the HARNESS as the party that failed to observe ("could not reap: ..."), peak and cpu
staying None because an unobserved process's usage is the third value, not a zero
(the `Cmd` docstring already states that rule for the spawn case). Rule 6 wants the
trigger to name the party, and here the party is internal - which is exactly why the
note must say so rather than borrowing the timeout's wording.

**Checks, both directions.** The fixture is in `done_when`: force `os.wait4` to raise
in-process (patch `os.wait4` in the test process - `run()` does `import os` locally, so
the patch must hit the module, as the probe did), run a command whose true exit is 3,
and assert what comes back is 127-plus-note, not 0. The control is the same command
unpatched reading 3. A mutant that restores `reaped.put((0, None))` must go red on the
fixture and leave every existing check green - it is a variant question too: the
timeout and spawn paths must still read 124 and 127 after the change.

## note 2026-08-29

Done on branch task-213-static-reap-fail-closed, PR #92, one clean CodeRabbit round (LANDED_COMMENT, no actionable comments), head f8dc5d9e65d50617a864f9202ad2f94622037d7c.

**The fix.** The waiter's except branch now puts the exception object as the sentinel status (never 0); `run()` detects a non-int status and decodes it as 127 with `note="could not reap: <exception>"` - the HARNESS named as the party that failed to observe (rule 6, internal party). `ru` stays None so peak_rss_mb/cpu_seconds are None. When a reap failure follows a timeout (post-kill `get` delivers the sentinel), code stays 124 and the note reads "TIMEOUT after Ns; could not reap: ...". The pure-timeout note is byte-identical to before.

**Pinned in eval/judge/rusage_selftest.py** (`test_reap_failure_is_not_exit_zero`, `test_reap_mutant_is_caught`): fixture patches `os.wait4` in-process - `run()` does `import os` locally, so the module attribute is the only seam - to raise ChildProcessError over a child whose true exit is 3. Red-first established against the unfixed module: forced run read exit=0 with note='' (4 FAILs), control and both neighbours green in the same run. After the fix: 127, could-not-reap note, both stream lines preserved, resource fields None, stored record saying the same; unforced control reads 3; spawn path 127/could-not-run and timeout 124/TIMEOUT asserted unchanged in the same check.

**The mutant is automated.** `test_reap_mutant_is_caught` reads static.py's source, replaces the anchor `reaped.put((ex, None))` with `reaped.put((0, None))`, and exec's it into a separate module - registered in sys.modules BEFORE exec, because @dataclass resolves string annotations via sys.modules (the exact failure static.py's own loader comments about at its lines 38-42). The mutant must reproduce exactly the exit 0 the fixture refuses; a missing anchor raises loudly, so a manual revert of the fix goes red twice. Demonstrated the whole-suite shape too: with static.py reverted on disk, the suite showed the 4 fixture FAILs and every pre-existing check green.

**Gates:** rusage_selftest exit 0 unpiped; capture_selftest 39/39 exit 0; runner_capture_selftest 50/50; docstat --sweep clean; lint.py --gate --rule invalid-syntax clean; ruff adds no finding (the B905 at analyse_frames pre-exists on HEAD, baselined); tasks.py check clean; branch even with origin/main d3b97bf.

**For whoever audits for other fabricated statuses:** the post-kill `reaped.get(timeout=60)` Empty fallback also assigns `status, ru = 0, None`, but there `timed_out` is already True, so `code` reads 124 with the TIMEOUT note - that site cannot produce a green gate and was deliberately left alone. Also note `Cmd.tail` returns the note alone when a note is set, so a reap failure's tail is the note, same convention as a timeout.

**Not a finding from me:** nothing stored was produced by the channel - every stored grading came from a wait4 that returned (the same channel-not-wrong-number split as tasks/211). Whether it merits a finding number is the orchestrator's allocation at merge.
