# Public repository data policy

This repository contains schemas, calculation code, documentation, and reviewed synthetic
fixtures only. It must not contain customer evidence, internal deployment configuration, raw work
logs, credentials, kubeconfigs, infrastructure state, or generated customer scorecards.

Before committing:

1. Confirm every example is synthetic and label it as such.
2. Inspect staged filenames and content, not only the working tree.
3. Keep raw evidence and customer economics outside the repository.
4. Store only aggregate role-level effort; never compensation or personal time records.
5. Treat cluster names, private registries, tenant IDs, endpoints, and workload payloads as
   deployment data unless explicitly approved for publication.
6. Run secret scanning and tests before pushing to `main`.

`.gitignore` is a guardrail, not proof that content is safe. Already-tracked files bypass ignore
rules and require explicit review.
