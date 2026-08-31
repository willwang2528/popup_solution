# The OK Is Not Enough rule snapshot

- Upstream repository: `https://github.com/the-ok-is-not-enough/scala-appanalyzer`
- Frozen revision: `b618948c0d24b917b3a46a88f5c1cf6ff84571cd`
- Upstream path: `resources/consent/indicators.json`
- Upstream file SHA-256: `2618308cc0ff4234fe47ac39a584e1c51b372a6050fc9621c87705f2eb1b6c8f`
- Vendored file SHA-256: `8b376a5391e76abef6b73b2889129ed36c64b4fd096fa4e1c51d781493bf34c9`
- License: MIT; the upstream notice is preserved in `LICENSE`.
- Fixed upstream example configuration: `keywordThreshold=1`,
  `maxSizeFactor=1.5`. The v1 no-action detector uses only the former because
  button selection and clicking are outside scope.

The vendored JSON has the same parsed content as upstream; the only byte-level
difference is a final newline. The Python port preserves the
upstream dialog/link/regular/half-keyword decision and adds only a deterministic
projection of contributing Appium element text as `message_text_pred`. That
projection is a benchmark adaptation, not an upstream output. The adapter accepts
only Appium-like structured channels (`structured`, accessibility/UIAutomator,
and XCUI/XCTest); DOM and protocol text are excluded.
