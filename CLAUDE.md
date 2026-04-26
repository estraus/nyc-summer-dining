# Interaction style

- Operate autonomously. Do not ask the user clarifying questions, do not pause for confirmation, and do not present options for them to pick from.
- Two exceptions where you MUST ask first:
  1. The action will cost the user money (paid API calls, cloud spend, billable services, package purchases, deploys that consume metered resources, etc.).
  2. The action introduces a security risk (exposing secrets, weakening auth, granting broad permissions, running untrusted code, modifying ACLs, force-pushing shared branches, etc.).
- Outside those two cases, make a reasonable decision and proceed. If a choice is ambiguous, pick the most defensible option, note it in your end-of-turn summary, and move on.

# Git / PR workflow

- When work is complete, open a PR and merge it to main without asking. Resolve any merge conflicts before merging.
- Prefer squash merges to keep history clean.
