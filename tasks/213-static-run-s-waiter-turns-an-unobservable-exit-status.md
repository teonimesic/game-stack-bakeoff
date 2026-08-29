---
id: 213
title: static.run's waiter turns an unobservable exit status into exit 0 - the one fail-open fallback in the tier-1 measurement path
status: todo
priority: 5
refs: eval/judge/static.py, eval/judge/rusage_selftest.py
done_when: 'a fixture that forces os.wait4 to raise (ChildProcessError, in-process, the way this ticket''s probe did) takes static.run over a command whose true exit is nonzero and gets back NOT exit 0 - the module''s existing convention for an unspawnable binary (code 127) with a note in `note` that names the HARNESS as the cause ("could not reap: ..."), streams preserved, peak_rss_mb and cpu_seconds None (the honest third value, not 0.0) - pinned red-first in eval/judge/rusage_selftest.py (whose subject is already what static.run observes) with the unforced control still reading the true exit; the spawn-failure path keeps its 127 and the timeout path keeps its 124-with-note, both asserted unchanged in the same check; python3 eval/judge/rusage_selftest.py exits 0 unpiped after, and python3 eval/judge/capture_selftest.py is unaffected (it drives static.run over real children on every check).'
established_by: 'Measured 2026-08-29 by the ninth cleanup pass, before filing: an in-process probe (/tmp/pa92-wait4probe.py, since deleted with the session) patched os.wait4 to raise ChildProcessError and ran static.run over `sh -c "exit 3"`; it reported exit code 0, note empty, both streams empty, peak/cpu None - while the unforced control over the same command read the true 3. static.py line ~168 is the only `put` of a fabricated status in the module: `except (ChildProcessError, OSError): reaped.put((0, None))`, which the main flow reads as `os.waitstatus_to_exitcode(0)` = 0.'
pr: (none yet)
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
