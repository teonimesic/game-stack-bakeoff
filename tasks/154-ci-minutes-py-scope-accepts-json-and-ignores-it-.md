---
id: 154
title: ci_minutes.py --scope accepts --json and ignores it, and the selftest calls that a VARIANT
status: in_progress
priority: 3
refs: eval/tools/ci_minutes.py main() and filter_problems, .github/workflows/controls.yml scope step, .github/workflows/README.md, AGENTS.md rule 13, PR 31
done_when: 'Either (a) main() rejects --scope --json with a non-zero exit and a message naming the unsupported combination, and filter_problems reclassifies that command as a MUTANT with the selftest still exit 0; or (b) --scope honours --json and emits its scope decision as JSON, with the variant kept and a row asserting the JSON is parseable and carries the relevant verdict. Either way: state which was chosen and why, ci_minutes.py --selftest exits 0 unpiped, and the mutant/variant counts in its closing line are re-read rather than carried forward. A third acceptable outcome is a measured NO - evidence that the flag combination is unreachable from any workflow the repository can hold - but the current variant text says the opposite, so that would have to explain the variant away.'
---

main() dispatches --selftest, then --scope, then --gates, and only the --gates branch reads args.json. So `ci_minutes.py --scope --json` exits 0 having silently ignored the flag. That is the shape AGENTS.md rule 13 names: an accepted-but-ignored flag is worse than an unsupported one, because exit 0 reads as "the command did what I asked". It is worse here than in general, because filter_problems classifies exactly that command as a VARIANT - an input the check must not redden - so the selftest actively asserts that a scope step invoked with a flag it does not honour is a correct scope step. A workflow edited to `ci_minutes.py --scope --json` would pass every pin. Found by CodeRabbit on PR 31, on code that arrived from main in task 148 and is outside that PR https://github.com/teonimesic/game-stack-bakeoff/pull/31 diff, which is why it was not fixed there.
