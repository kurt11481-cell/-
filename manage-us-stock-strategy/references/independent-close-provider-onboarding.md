# Independent Completed-Close Provider Onboarding

The structured provider adapter is a disabled acceptance framework. A provider
must not be enabled merely because credentials or an endpoint exist.

Required acceptance evidence includes provider identity, capability mapping,
point-in-time support, session and timestamp semantics, raw versus adjusted
basis, corporate-action behavior, rate limits, failure handling, sample
comparisons, Shadow-session results, policy version, and explicit user approval.

States are:

- `CREDENTIALS_NOT_CONFIGURED`
- `SHADOW_ACCEPTANCE_PENDING`
- `SHADOW_ACCEPTANCE_FAILED`
- `USER_APPROVAL_PENDING`
- `APPROVED_DISABLED`

Activation requires a complete schema-valid record and explicit policy/user
authority. Unknown fields fail closed. The adapter must never silently use a
second Yahoo route, stale data, adjusted data, retry storms, or credential
material in logs.
