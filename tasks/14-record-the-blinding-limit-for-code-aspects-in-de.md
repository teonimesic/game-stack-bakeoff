---
id: 14
title: Record the blinding limit for code aspects in DECISIONS.md
status: open
priority: 2
refs: eval/FINDINGS.md #53, eval/judge/anonymise.py
done_when: DECISIONS.md states that code-reading aspects are not language-blind, why it cannot be fixed, and what follows for their use; and FINDINGS #53 points at that decision instead of carrying the open question itself
---

Every judge brief promises the judge is not told which stack a submission came from. For the two code-reading aspects that promise is false, and cannot be made true.

THE MECHANISM: anonymise.py flattens paths to sim/01.gd, view/03.rs, src/02.ts, view/06.cs - and KEEPS THE EXTENSION. One extension per stack, uniquely identifying, in every file the judge opens.

WHY IT IS UNFIXABLE RATHER THAN UNFIXED: 'idiomatic' asks whether the code is written the way its language is normally written. You cannot judge whether Rust reads like Rust without knowing it is Rust. Stripping the extension would not blind the judge anyway - the syntax is unmistakable in the first line of any file. The aspect whose subject IS the variable under test cannot be blinded to that variable.

WHY THIS BELONGS IN DECISIONS.md: it is currently carried inside a findings entry as an open sore. It is not a defect to be fixed, it is a permanent property of the design, and a permanent property with consequences for how a result may be used is a decision. FINDINGS is for what went wrong and what it taught; DECISIONS is for what is settled and why.

WHAT TO WRITE: that code aspects see the language; that this is inherent for 'idiomatic' and incidental but unavoidable for 'architecture'; that neither may contribute to a cross-stack ranking (already pre-registered in RUBRIC.md); and that within-stack A/B comparison is unaffected, because a per-stack prior cancels when the stack is held constant. That last point is what the template improvement loop actually needs.

Documentation only. No measurement required.
