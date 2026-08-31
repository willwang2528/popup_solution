# Local macOS PMJ Vision OCR Ledger (Public Copy)

### env: pmj-vision-ocr@9c9523d9

- how: local macOS Vision framework through a pinned Swift CLI; orchestration uses the project `.venv/bin/python3`
- shape: local macOS 26.2 arm64; no network, paid API, GPU allocation, GUI automation, or mobile-device action
- spec: `popup-solution/experiments/v1-message/ocr/compute/local-macos-pmj-ocr.env-spec.json`
- canonical public spec SHA-256: `9c9523d9e6d368cb543cb75448f6abd4dfc5ebcc2ee0b634ac852505ecf82524`
- public spec file-bytes SHA-256: `a5ce55cc070bc1937c12094b090207d78a3291a82d3289cd45164dc19e831782`
- Swift source SHA-256: `b77d6b9d7694e7c3ba816d20bd58ad9f3752fa3b58734e67895002b4c0e2096b`
- Python adapter SHA-256: `bf59d2c3001df4acd11b1ca4dcb06ca212a9ca94bc78de218c77d9c27d5245b2`
- formal input: `popup-solution/dataset-v1/work/annotation-media/pilot-batch-30/pilot-manifest.jsonl`
- formal input SHA-256: `2df7c98d78787e880da28469c4face345b7d0b0185a463753b5c80717ff5aabf` (30 rows)
- build resolution: `xcrun --sdk macosx15.4 swiftc`, target `arm64-apple-macosx15.4`, project-local module cache
- tier 1: PASS — Swift 6.3.2 executable and macOS 15.4 SDK resolved
- tier 2: PASS — `WITNESS vision_ocr seed=17 observations=0 revision=3`
- formal local batch: PASS — 30/30 rows, 30 text-observed, 0 no-text, total recorded Vision latency 7261.791959 ms
- private predictions SHA-256: `220fb08fcf6b452656f27fbae6fc7a90093b00b45a54112805e86fb092409be1`
- compiled engine SHA-256: `b66aa48e0ad715b673eb027289f4502b365c9982526c9a0174febafb5b2d082c`
- public artifact: `popup-solution/experiments/v1-message/ocr/PUBLIC_RUN_SUMMARY.json`
- privacy status: `withheld_pending_privacy_review`; raw images and derived OCR text stay gitignored and are not public artifacts
- empirical claim status: unscored OCR evidence only; every private row abstains on popup presence and has `paper_result_eligible=false`
- tier 3: PASS — fresh agent ran the documented command verbatim; restricted sandbox produced the documented fail-closed `nilError`, then the identical authorized local command exited 0 with 7/7 tests passing in 42.435 s
- final standalone-repo root check: PASS — current test file SHA-256 `27e28236a8786e036a5fdd09e74f0826feb0391335dd53a04c3ce25ff5eeed53` ran 7/7 on the authorized host in 41.558 s
- gotcha: the default Command Line Tools macOS SDK is compiler-build incompatible on this host; pin `macosx15.4`
- gotcha: the default clang module cache is outside the project sandbox; use `.build/module-cache`
- gotcha: restricted filesystem execution can block Vision system services (`nilError` or CVPixelBuffer `NSOSStatus -6662`); treat this as blocked and rerun the unchanged command only in an authorized local macOS execution context
