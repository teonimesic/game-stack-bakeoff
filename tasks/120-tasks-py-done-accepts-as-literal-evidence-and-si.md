---
id: 120
title: tasks.py done accepts - as literal evidence and silently writes a one-character durable record
status: in_progress
priority: 4
refs: 'eval/tools/tasks.py cmd_done and cmd_note, tasks/112, FINDINGS #80'
done_when: 'Either tasks.py done reads evidence from stdin on - the way note does, or it rejects a bare - with a non-zero exit and a message naming the alternative. Pinned both directions: a control shows the old behaviour writing the 1-character record and the new behaviour either storing the full text or exiting non-zero, and a normal inline evidence string still stores unchanged. Whichever is chosen, note and done agree on what - means. tasks.py check and docstat.py --sweep exit 0 unpiped.'
---

tasks.py note takes - to read the section from stdin and its help says so is the only safe way to pass backticks or newlines (#80). tasks.py done takes no such option, and its evidence string is at least as durable - it is the established_by line every later reader trusts. Under task 112 the obvious call, done 112 - < file, was accepted and recorded established_by=- , a 1-character record replacing 2100 characters of measurement, with exit 0 and no warning. That is #80's shape moved from backticks to a stdin sentinel: the record is silently emptied and nothing reports it. It fails open, so the loss is only visible to someone who re-reads the ticket afterwards. Two sibling commands disagreeing about - is also the enumeration failure AGENTS.md keeps recording: the safe path was added where the problem had been seen, not where the property lives.
