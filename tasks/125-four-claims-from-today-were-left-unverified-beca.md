---
id: 125
title: Four claims from today were left unverified because the case that would test them did not arise
status: in_progress
priority: 3
refs: 'eval/findings/certifies-nothing.md #152 #153 #156, eval/tools/coderabbit_config.py, eval/tools/docstat.py duplicate-fragment and orphaned-tail, .coderabbit.yaml'
done_when: each of the four is either verified with the measurement stated, or closed with why it still cannot be tested and what would change that; the SkillSpector one requires a real pull request that edits a SKILL.md, and reporting zero attachments without one does not close it
---

Each was stated honestly as unestablished by the agent that shipped it, and each is now cheaply testable because the blocking condition has passed. Left together because they are one question - a check whose triggering case has not occurred is indistinguishable from a check that cannot fire - and separately none is worth a dispatch. (1) FINDINGS 153: SkillSpector was disabled and the pull request that disabled it touched no SKILL.md, so its zero attachments are zero for the wrong reason; any pull request editing a skill settles it. (2) FINDINGS 153: a misspelled tool key in .coderabbit.yaml is accepted and silently ignored, because that schema does not forbid unknown properties - it was documented rather than gated because confirming it needed the network. (3) FINDINGS 152: the stranded-tail gate has a corpus census of 0, so it is protecting silently and its only known instance is historical. (4) FINDINGS 156: the 12-word window was chosen against a 183-document corpus with two words of margin over the nearest antithesis, and the corpus grows daily.
