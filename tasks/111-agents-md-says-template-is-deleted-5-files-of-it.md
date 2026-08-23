---
id: 111
title: AGENTS.md says template*/ is deleted; 5 files of it are still tracked on main
status: in_flight
priority: 3
refs: AGENTS.md line 28, DECISIONS.md 'The four template*/ trees and the spec-change suite are retired', .gitignore
done_when: either the 5 remaining template-ts/ and template-unity/ paths are removed from git tracking and origin/main, or AGENTS.md line 28 and the DECISIONS.md retirement section are corrected to state what is actually still there and why it was kept. Whichever is chosen, git ls-tree -r --name-only origin/main | grep '^template' and the text of AGENTS.md must agree, and the answer must be checked against origin/main rather than a worktree
---

AGENTS.md is always loaded and states 'template*/ is deleted (DECISIONS.md, #122)'. git ls-tree -r --name-only origin/main | grep '^template' returns 5 paths: template-ts/.eslintcache, template-ts/public/main.js, and three build outputs under template-unity/tools/analyzer/bin/ (.deps.json, .dll, .pdb). None is source. Two of the five are exactly the kind of build artefact .gitignore exists to keep out - an eslint cache and a compiled analyzer with its pdb - so the deletion pass removed the trees but left behind the files git was already tracking before the ignore rules covered them. A live always-loaded document stating something false is the defect class this project treats as worse than silence, because it will be followed. It also affects the reversal condition in DECISIONS.md, which promises restoration via git checkout of a pre-retirement commit: a reader seeing template-ts/ still present may believe the retirement was partial. Noticed while configuring CodeRabbit for task 108; the analyzer .dll would also be shipped to a code reviewer as an unreviewable binary.
