---
id: 185
title: capability.py's TRIAL_RE does not match a scene trial, so the scene submission is stack '?' and invisible to the four-arm gate
status: in_review
priority: 3
refs: eval/judge/capability.py,eval/SCENES.md
done_when: a scene trial id parses to its game and its stack, so wg-scene-s1ts-2026-08-25/s1_parallax__ts__t0 reports under 'ts' rather than '?' - or the module states in code that the four-arm gate is asked of game submissions only and reports how many records it excluded, so a reader can see the population. Either way a control that hands the sweep a scene record and asserts which population it lands in, red before green.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/61
---

capability.TRIAL_RE is ^(g\d+_[a-z0-9]+)__([a-z]+)__t(\d+)$, so the one stored scene submission, wg-scene-s1ts-2026-08-25/s1_parallax__ts__t0, parses as game '?' stack '?'. It is a ts submission. Every per-stack partition in the module therefore excludes it: the distribution tables print a '?' row of n=1 beside the four arms, and no_stack_correlated_gap and stack_skew_warnings both filter on ARMS, so its fields are never asked the question the gate exists to ask. The gate still reports 'no stack-correlated gap' - it is not wrong, it is answering over 68 of the 69 records without saying so. It found nothing today because the scene's fields are all populated; a scene submission with a genuine per-arm absence would be silently uncounted. Found while doing tasks/182, which left it alone as out of scope.
