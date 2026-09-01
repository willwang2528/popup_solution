package org.pmab.collector.core;

import java.util.Objects;

public final class CaptureTimingGate {
    private CaptureTimingGate() {}

    public static TimingDecision evaluate(TimingEvidence evidence, long maximumDeltaMs) {
        boolean ordered = evidence.treeBeforeStartUptimeMs() <= evidence.treeBeforeEndUptimeMs()
                && evidence.treeBeforeEndUptimeMs() <= evidence.screenshotRequestUptimeMs()
                && evidence.screenshotRequestUptimeMs() <= evidence.screenshotResultUptimeMs()
                && evidence.screenshotResultUptimeMs() <= evidence.screenshotCallbackUptimeMs()
                && evidence.screenshotCallbackUptimeMs() <= evidence.treeAfterStartUptimeMs()
                && evidence.treeAfterStartUptimeMs() <= evidence.treeAfterEndUptimeMs();
        if (!ordered) {
            return new TimingDecision(false, "invalid_monotonic_order");
        }
        long beforeDistance = evidence.screenshotResultUptimeMs() - evidence.treeBeforeEndUptimeMs();
        long afterDistance = evidence.treeAfterStartUptimeMs() - evidence.screenshotResultUptimeMs();
        if (Math.max(beforeDistance, afterDistance) > maximumDeltaMs) {
            return new TimingDecision(false, "synchronization_delta_exceeded");
        }
        if (!Objects.equals(evidence.beforeTreeHash(), evidence.afterTreeHash())) {
            return new TimingDecision(false, "tree_hash_drift");
        }
        if (evidence.eventSequenceBefore() != evidence.eventSequenceAfter()) {
            return new TimingDecision(false, "accessibility_event_drift");
        }
        if (!Objects.equals(evidence.focusTokenBefore(), evidence.focusTokenAfter())) {
            return new TimingDecision(false, "focus_drift");
        }
        return new TimingDecision(true, "accepted");
    }
}
