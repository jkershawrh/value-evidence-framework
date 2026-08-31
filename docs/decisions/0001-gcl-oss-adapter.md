# ADR 0001: Wait for the GCL OSS contract

Status: accepted

The GCL integration remains a contract fixture with zero claimed financial value until the GCL OSS
version is ready. VEF will then consume a versioned export owned by GCL OSS. It will not scrape
implementation details or infer avoided impact from decision counts.

This keeps both projects independently releasable and preserves the distinction between evidence
that GCL evaluated or rejected an action and evidence that a customer loss was counterfactually
avoided.
