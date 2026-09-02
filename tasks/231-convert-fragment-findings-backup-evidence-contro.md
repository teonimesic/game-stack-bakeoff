---
id: 231
title: Convert fragment/findings/backup_evidence controls to the default-mutant sweep
status: done
priority: 3
refs: 'eval/tools/corpus_control.py (the sweep template and its PR #54 docstring), eval/tools/withdrawn_control.py (converted 2026-09-01, the second instance), .github/workflows/README.md (the corpus_control and withdrawn_control narrative rows)'
done_when: 'Each of fragment_control, findings_control and backup_evidence_control: default invocation runs the clean pass and every named mutant in one process (corpus_control.sweep / the converted withdrawn_control.sweep are the templates - leak-checked restore between mutants, SURVIVED reported and exit 1 on any survivor), --clean-only preserves the controls-alone mode, --mutate NAME unchanged. Every mutant verified to flip (the suite''s own sweep output), SURVIVED detection verified against a deliberately neutered mutant copy, new step cost measured with time and written beside the number in .github/workflows/README.md''s gates.yml section, and the register narrates each converted step the way it narrates corpus_control and withdrawn_control.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/110
established_by: 'squash 3d6a028 on main. Verified on the merged tree: fragment_control 8/8 mutants died, backup_evidence_control 5/5, findings_control 9/9, all default invocations exit 0; findings_control --selftest 8/8 assertions including the 4 new mode-refusal rows. Review round: 3 threads (citation links linkcheck-verified, digits for mutable counts, mutually exclusive mode flags pinned red-first). Register conflict against task 229 resolved by union, each side keeping the paragraph it owns. Local branch deletion deferred: checked out in worktree agent-a81a6929a3f5caa29, on the cleanup list'
---

Pass 44 (2026-09-01, eval/tools/withdrawn_control.py read whole) measured the class: five controls carry a --mutate mode, and corpus_control's sweep() docstring states the principle with its cost - 'A suite whose mutants are opt-in is a suite whose mutants are the one thing nobody re-runs' (raised by CodeRabbit on PR #54). Until 2026-09-01 withdrawn_control had the same shape; its CI step ran bare while its five mutants - the recorded justification for the withdrawal register gating at all (docstat.py's wiring note credits the five flips) - ran only when an operator asked. withdrawn_control is converted (default = clean + all 5 mutants, ~15s locally with the historical-corpus cache shared across mutant runs; SURVIVED detection proven by a neutered-mutant copy exiting 1). The three named here still have the opt-in shape: fragment_control (its whole_line mutant is the design measured as a complete false negative, per the register - exactly the mutant a future reader must be able to watch die), findings_control, backup_evidence_control. evidence_set_control's mutants are reachable by nobody, but its whole script is left out of CI with a recorded reason (register: exit 2 UNMEASURABLE without eval/runs/) - mention it in the conversion commit, do not convert it here.

## note 2026-09-01

Done on branch task-231-default-mutant-sweep, PR #110, head bd85ab2.

WHAT WAS DONE. fragment_control (8 mutants), findings_control (9) and backup_evidence_control (5)
all converted to the corpus/withdrawn default-sweep shape: the bare invocation runs the clean pass
plus every named mutant in one process, leak-checked restore between mutants, SURVIVED reported,
exit 1 on any survivor or clean failure. --clean-only preserves the controls-alone mode; --mutate
NAME is unchanged. findings_control keeps --all-mutants as a documented alias of the sweep, because
deleting it left the pass-39 record in CLEANUP-LOG.md naming a flag with no argparse - docstat
--sweep caught that on this branch's first gate run. backup_evidence_control now refuses
--mutate with --runs-root loudly (accepted-but-ignored flag, rule 13). The register
(.github/workflows/README.md) narrates all three conversions with the time command beside each
figure, and gates.yml carries the step comments. evidence_set_control is deliberately NOT converted
per the ticket: its whole script stays out of CI in the exclusion table, exit 2 UNMEASURABLE without
eval/runs/.

ESTABLISHED. 22 of 22 mutants verified to flip from each suite's own sweep output. SURVIVED
detection proven per suite against a deliberately neutered mutant copy run in a throwaway file:
fragment in both branches (rebound-nothing, and rebinds-but-flips-nothing), findings and backup by
a patch that applies and changes nothing, each reading SURVIVED at exit 1. Timings measured with
time: fragment sweep 4.5s (clean-only 0.65s), findings sweep about 25s (readings 24.5 and 27.0,
quoted as "about"), backup sweep 0.75s. The findings leak check is a byte snapshot of the
repository's own docstat.py (its mutants are text patches on a copy, so there is no module-global
surface); backup's restore is load-bearing because apply_mutant closes over the attribute's current
value.

NO FINDING NUMBER needed: the two defects docstat --sweep caught mid-branch (the dangling
--all-mutants citation; a 12-word duplicate fragment in the first register wording) were fixed
in-branch and are narrated in the commit message.

REVIEW. The review wait expired UNRESOLVED - 40 polls over 20m19s at bd85ab2, no review, summary
or round ever seen in flight - and the fact was posted on the PR
(#issuecomment-5498131360). Both required checks pass at that head: gates 3m20s, controls 17m40s.
Main had not moved when last fetched, so the branch is current with its base.
