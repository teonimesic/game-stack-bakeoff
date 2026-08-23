---
id: 104
title: EVIDENCE_BLURB tells every judge the pack is truncated by a size budget that was removed on 2026-08-22
status: open
priority: 3
refs: 'eval/judge/field.py EVIDENCE_BLURB, eval/FINDINGS #69, tasks/95'
done_when: the sentence is either corrected to what is true now or removed, with a note in eval/RUNS.md recording that every stored round read the stale text; and a check exists that would fail if a claim in EVIDENCE_BLURB stops matching the packer - a sentence about the packer that no code reads is how this one survived a year
---

field.EVIDENCE_BLURB['code'] reads: NOTE: the pack is filled until a size budget runs out, so it may not contain every file the author wrote - judge what is here and do not infer that an absent concern was neglected. The character budget was REMOVED on 2026-08-22 (FINDINGS 69) and files_dropped_for_length is now 0 by construction, asserted by the completeness gate in field.build_pack. So the harness tells every judge, in the brief, that its evidence may be an alphabetically-selected subset when it is not. The direction of the error matters: it invites a judge to discount an absence it is actually seeing in full, which is the opposite of the caution the sentence was written to induce. Found while closing task 95, which repaired CHANGED.txt in the same function; not fixed there because judge-facing text is what the judge reads and changing it is a change to the instrument, not to a leak. It should be corrected before the next round rather than after.
