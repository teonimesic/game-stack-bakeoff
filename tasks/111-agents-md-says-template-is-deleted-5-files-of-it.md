---
id: 111
title: AGENTS.md says template*/ is deleted; 5 files of it are still tracked on main
status: open
priority: 3
refs: AGENTS.md line 28, DECISIONS.md 'The four template*/ trees and the spec-change suite are retired', .gitignore
done_when: either the 5 remaining template-ts/ and template-unity/ paths are removed from git tracking and origin/main, or AGENTS.md line 28 and the DECISIONS.md retirement section are corrected to state what is actually still there and why it was kept. Whichever is chosen, git ls-tree -r --name-only origin/main | grep '^template' and the text of AGENTS.md must agree, and the answer must be checked against origin/main rather than a worktree
---

AGENTS.md is always loaded and states 'template*/ is deleted (DECISIONS.md, #122)'. git ls-tree -r --name-only origin/main | grep '^template' returns 5 paths: template-ts/.eslintcache, template-ts/public/main.js, and three build outputs under template-unity/tools/analyzer/bin/ (.deps.json, .dll, .pdb). None is source. Two of the five are exactly the kind of build artefact .gitignore exists to keep out - an eslint cache and a compiled analyzer with its pdb - so the deletion pass removed the trees but left behind the files git was already tracking before the ignore rules covered them. A live always-loaded document stating something false is the defect class this project treats as worse than silence, because it will be followed. It also affects the reversal condition in DECISIONS.md, which promises restoration via git checkout of a pre-retirement commit: a reader seeing template-ts/ still present may believe the retirement was partial. Noticed while configuring CodeRabbit for task 108; the analyzer .dll would also be shipped to a code reviewer as an unreviewable binary.

## The ticket's diagnosis is wrong, and the real one is worth keeping (2026-08-23)

"The deletion pass removed the trees but left behind the files git was already tracking before
the ignore rules covered them" does not survive the artifacts. **The deletion pass was complete.**
git ls-tree -r --name-only e86e09d matches 0 paths under template*/, and so does its other merge
parent 5afeb31. The MERGE, f315f7e, carries 5. They came from neither parent - they came off the
disk.

The mechanism: **each tree carried its own .gitignore, and deleting the tree deleted the ignore
rules that had been hiding its build output.** git show 5afeb31:template-ts/.gitignore lists
public/main.js and .eslintcache; git show 5afeb31:template-unity/.gitignore lists
/tools/analyzer/bin/ under a comment saying only the intermediate build tree is ignored. Once
those files were gone, a git add -A at merge time saw an eslint cache, a 1.2M esbuild bundle and
a compiled analyzer with its .pdb for the first time, and staged them. The removal and the loss
of the guard land in the same commit; the re-add lands in the next one, where it reads as an
unrelated file rather than as a botched deletion.

That changes the remedy. If the cause had been "tracked before the ignore rules", git rm --cached
plus per-class ignore rules would be the fix. Because the cause is an un-ignored build tree meeting
add -A, the fix is git rm plus a root .gitignore entry scoped to template*/ - which is what shipped,
proved in both directions: with the entry, git add -A over three replanted artefacts stages nothing
and the deletions stand; without it, the same command un-deletes all three. A general **/bin/ rule
was rejected on measurement, not on taste - it also matches
eval/starters/rust/crates/game/src/bin/film.rs and .../sim/src/bin/probe.rs, which are Rust source.

**What was NOT done, and it is the residual risk.** No gate compares a document's claim that a tree
is deleted against the tree. From f315f7e (2026-08-23 08:35 -0300) until this repair the same day,
nothing in the repository could have disagreed with AGENTS.md; a person configuring a code reviewer
found it. The .gitignore entry closes the recurrence path it names; it does not detect a recurrence
by some other path.

**The same shape is live elsewhere and is task 114's, not this one's.** AGENTS.md says
.agents/skills/ "held exactly that until 2026-08-23" - past tense - and git ls-tree -r --name-only
origin/main returns 9 .agents/skills/*/SKILL.md paths. That one IS gated: docstat.py --sweep
reports all 9 and exits 1, which is the pre-existing baseline failure any agent on this branch
will see. The diff of --sweep before and after this work is empty.
