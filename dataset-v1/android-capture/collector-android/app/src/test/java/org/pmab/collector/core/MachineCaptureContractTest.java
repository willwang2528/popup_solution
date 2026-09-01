package org.pmab.collector.core;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;

import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.Test;

public final class MachineCaptureContractTest {
    @Test
    public void collectorCannotSelfApprovePrivacyOrInsertGoldAndPredictions() {
        // Break caught: machine output impersonates post-capture human review or leaks labels.
        Map<String, Object> safe = new LinkedHashMap<>();
        safe.put("capture_id", "PMAB-A-CAP-001");
        safe.put("machine_status", "complete");

        assertFalse(MachineCaptureContract.containsHumanDecision(safe));

        for (String forbidden : new String[] {
            "privacy_review_status", "gold_label", "prediction", "method_prediction"
        }) {
            Map<String, Object> contaminated = new LinkedHashMap<>(safe);
            contaminated.put(forbidden, "passed");
            assertThrows(
                    IllegalArgumentException.class,
                    () -> MachineCaptureContract.requireMachineOnly(contaminated));
        }
    }
}
