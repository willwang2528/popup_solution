package org.pmab.collector.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class CaptureTimingGateTest {
    private static TimingEvidence validEvidence() {
        return evidence("tree-hash", 41, "window-7/node-2", 1200, 1300, 1400);
    }

    private static TimingEvidence evidence(
            String afterHash,
            long eventAfter,
            String focusAfter,
            long screenshotResult,
            long treeAfterStart,
            long treeAfterEnd) {
        return new TimingEvidence(
                1000,
                1100,
                1150,
                screenshotResult,
                1250,
                treeAfterStart,
                treeAfterEnd,
                "tree-hash",
                afterHash,
                41,
                eventAfter,
                "window-7/node-2",
                focusAfter);
    }

    @Test
    public void stableMonotonicTreeScreenshotTreeSequenceIsAccepted() {
        // Break caught: a valid no-action bracket can never produce a complete bundle.
        TimingDecision decision = CaptureTimingGate.evaluate(validEvidence(), 3000);

        assertTrue(decision.accepted());
        assertEquals("accepted", decision.reason());
    }

    @Test
    public void treeDriftEventDriftOrFocusDriftIsRejected() {
        // Break caught: changed UI state is paired as one synchronized observation.
        assertEquals(
                "tree_hash_drift",
                CaptureTimingGate.evaluate(
                                evidence("changed", 41, "window-7/node-2", 1200, 1300, 1400),
                                3000)
                        .reason());
        assertEquals(
                "accessibility_event_drift",
                CaptureTimingGate.evaluate(
                                evidence("tree-hash", 42, "window-7/node-2", 1200, 1300, 1400),
                                3000)
                        .reason());
        assertEquals(
                "focus_drift",
                CaptureTimingGate.evaluate(
                                evidence("tree-hash", 41, "window-8/node-9", 1200, 1300, 1400),
                                3000)
                        .reason());
    }

    @Test
    public void reorderedOrOverwideMonotonicBracketIsRejected() {
        // Break caught: self-reported timestamps outside the capture bracket pass synchronization.
        assertEquals(
                "invalid_monotonic_order",
                CaptureTimingGate.evaluate(
                                evidence("tree-hash", 41, "window-7/node-2", 1099, 1300, 1400),
                                3000)
                        .reason());
        assertEquals(
                "synchronization_delta_exceeded",
                CaptureTimingGate.evaluate(
                                evidence("tree-hash", 41, "window-7/node-2", 1200, 5001, 5100),
                                3000)
                        .reason());
    }
}
