# Popup Solution Research Instructions

Before planning, collecting literature, designing a method, defining a dataset, running an experiment, or drafting a contribution claim in this repository, read `RESEARCH_RULES.md` completely.

Treat `RESEARCH_RULES.md` as the user-authored research charter. Preserve it verbatim; update it only by an explicit resynchronization from the recorded Feishu source in `RESEARCH_RULES_PROVENANCE.json`.

Operational requirements:

- Keep the target population centered on blind and low-vision mobile users who use screen readers such as TalkBack or VoiceOver.
- Keep the intervention boundary to ordinary, authorized popup dismissal. Do not bypass CAPTCHA, risk controls, authentication, manual review, permission safeguards, payment confirmation, or other security controls.
- Every evaluated episode must cover popup identification, a dismissal or safe abstention decision, action execution when allowed, popup-specific disappearance evidence, context recovery, and original-task verification.
- Construct one dataset item as the union of fields supported by in-scope prior experimental methods and fields required by the proposed method. Preserve Android, iOS, mobile-Web, visual, accessibility, action, provenance, and verification semantics rather than flattening them destructively.
- Treat “first to formulate,” “first public dataset,” and “better metrics” as contribution targets that require novelty evidence and experimental support. Do not present them as established facts before the corresponding checks pass.
- Distinguish synthetic schema fixtures, controlled fixtures, paper reconstructions, real-device episodes, and target-user evidence. Never use a synthetic fixture as empirical proof.
- Keep durable research artifacts in this repository and make every material claim auditable through source location, evidence level, version, and Git history.

If a later instruction conflicts with the research charter, stop and obtain explicit user direction before changing the charter or expanding its boundary.
