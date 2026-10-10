---
title: Update
description: Brings in andamio's improvements and patches without touching yours.
---

```bash
andamio update --check   # what would change, touching nothing
andamio update           # apply it
```

Brings in andamio's improvements and security patches **without touching yours**: your
configuration, your apps, your secrets, your certificate and the inventory.

## How it works

Your copy was born from the template, so it doesn't share git history with it. That's why
`update` works **file by file**, with a three-way merge: yours, the andamio version you come
from, and the new one.

- What you never touched gets updated.
- What only you changed is kept.
- If both changed, it merges them. If they clash on the same lines, it leaves git-style
  conflict markers (`<<<<<<<` and `>>>>>>>`) for you to choose.

## When it's done

It requires a clean working tree before starting. If there were no conflicts, it offers to
push it as a single commit:

```
Push it now? (commit and push; `git revert HEAD` undoes it)
 › Yes, with the message 'andamio: update to 9606291a'
   Yes, I'll write the message
   No, I'll review it first (git diff)
```

And it tells you whether something needs applying on the server:

- **What runs on the server changed** (Ansible, scripts, stacks): apply it with
  `andamio server`.
- **Only andamio on your machine changed**: there's nothing to apply.

To undo a whole update: `git revert HEAD`.
