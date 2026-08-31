# B2 PopSweeper reproducibility gate

Frozen audit date: 2026-09-01

## Decision

An **exact PopSweeper + popup-ROI OCR baseline is NO-GO** with the currently
available artifacts. A separately named paper reconstruction may be implemented,
but it must not be described as the upstream system.

The decisive semantic mismatch is that the paper's YOLO-World component predicts
the **close-button bounding box**, not a popup-region bounding box. Feeding that
box to OCR would read the closing affordance area, not the popup message. A new
popup-region proposal would be this project's adaptation.

## What the paper fixes

- sample one frame every 100 ms;
- compare adjacent RGB histograms with reported threshold `0.8`;
- stage 1: ImageNet-pretrained ResNet50 with a
  `Linear → ReLU → Dropout → Linear → Sigmoid` head;
- stage 2: ImageNet-pretrained MobileNetV2, invoked after a positive stage 1;
- classifiers trained for 100 epochs with SGD + momentum and BCE;
- YOLO-World fine-tuned for 100 epochs at `640×640` on 832 popup images;
- YOLO-World output is a close-button `(x1,y1,x2,y2)` box.

Primary source: [PopSweeper arXiv 2412.02933v1](https://arxiv.org/abs/2412.02933v1),
with the repository's screened paper record in
[`data-collection/papers.jsonl`](../../data-collection/papers.jsonl). The fixed
claims above come from the method description of the classifier pipeline and
YOLO-World training/output; they do not infer unspecified parameters.

## Missing exact-reproduction assets

- official code repository and fixed code revision;
- ResNet50, MobileNetV2, and YOLO-World fine-tuned weights with hashes;
- classifier sigmoid thresholds and reported-but-unspecified training parameters;
- YOLO-World variant, base checkpoint, prompt/class, confidence/NMS/IoU settings,
  and multi-box selection rule;
- close-button bbox annotations;
- original GIF/time-series recordings and a trustworthy adjacent-frame manifest;
- a popup-region detector or popup ROI annotation (not part of the paper output);
- human popup-message gold.

The locally verified Zenodo basic archive contains 2,105 JPG files and supplies
folder-level labels, but no code, weights, bbox annotations, or temporal frame
sequence. Its official folder split also cannot automatically serve as the final
benchmark split: the local audit found exact-content and same-source groups that
must remain group-disjoint.

## Fail-closed exact gate

An execution may use the label `B2 exact PopSweeper` only if every box below is
resolved and frozen before test-gold access:

- [ ] official code URL, revision, and license;
- [ ] all model/checkpoint hashes and their licenses;
- [ ] frame order, interval, histogram implementation, threshold comparison, and
      first-frame rule;
- [ ] preprocessing, classifier thresholds, optimizer parameters, and seed;
- [ ] YOLO variant, prompt, thresholds, NMS/IoU, and multi-box policy;
- [ ] close-button bbox annotation provenance;
- [ ] no claim that the close-button bbox is a popup ROI;
- [ ] app/template-group-disjoint holdout with no train/validation overlap;
- [ ] completed blind A/B popup-message gold and final adjudication.

Any missing item rejects exact mode.

## Allowed alternatives

1. `B2R-static PopSweeper paper reconstruction + full-screen OCR`: implement
   reported architecture with validation-frozen missing parameters. This remains a
   reconstruction and is not official PopSweeper.
2. `B2A popup-region adaptation + ROI OCR`: add an independently specified popup
   region proposal. This is our method adaptation and must be evaluated separately.

Both alternatives remain action-free in v1. Raw images, crops, OCR text/bboxes,
app identifiers, and item-level predictions stay private; public artifacts may
contain only aggregate counts and hashes.
