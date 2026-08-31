# Popup Solution Research Instructions

Before planning, collecting literature, designing a method, defining a dataset, running an experiment, or drafting a contribution claim in this repository, read these files completely and in order:

1. `RESEARCH_RULES.md` — verbatim user-authored Feishu charter;
2. `RESEARCH_RULES_AMENDMENT_V1.md` — the user's later, authoritative v1 scope reduction.

Preserve `RESEARCH_RULES.md` verbatim. Update it only through an explicit resynchronization from the Feishu source recorded in `RESEARCH_RULES_PROVENANCE.json`. The amendment overrides earlier operational language only for the v1 success definition; it does not widen the safety boundary.

Operational requirements:

- Keep the target population centered on blind and low-vision mobile users who use screen readers such as TalkBack or VoiceOver.
- Keep v1 to popup presence and popup-message judgment. Read structured UI/accessibility representations first and use visual evidence only when the structured message is absent, merged, contradictory, or incomplete.
- Do not execute popup actions in v1. Dismissal, focus restoration, page restoration, and original-task recovery are advanced targets, not v1 success gates.
- Keep the observation boundary to ordinary, authorized popups. Do not bypass CAPTCHA, risk controls, authentication, manual review, permission safeguards, payment confirmation, or other security controls.
- Construct one dataset item as the union of fields supported by in-scope prior experimental methods and fields required by the proposed method. Preserve Android, iOS, mobile-Web, visual, accessibility, provenance, message, action, and advanced-recovery semantics rather than flattening them destructively.
- Treat `VPMA = popup-presence correct AND message semantically correct AND no critical hallucination` as the v1 item-level success value. Report detection F1, critical-information recall, critical-hallucination rate, abstention/coverage, visual calls, and latency separately.
- Keep `D`, `C_tech`, `C_a11y`, `T`, `VTR-tech`, and `A-VTR` nullable and excluded from v1 success. A required JSON container does not make its advanced contents required v1 evidence.
- Treat “first to formulate,” “first public dataset,” “better metrics,” and “improved user experience” as contribution targets requiring evidence. Never state them as established facts before the corresponding novelty check, public release, experiment, or target-user study passes.
- Distinguish synthetic schema fixtures, controlled fixtures, paper reconstructions, real-device episodes, and target-user evidence. Never use a synthetic fixture as empirical proof.
- Keep durable research artifacts in this repository and make every material claim auditable through source location, evidence level, version, and Git history.

If a later instruction materially changes this scope again, record a new amendment instead of editing the verbatim Feishu charter.
