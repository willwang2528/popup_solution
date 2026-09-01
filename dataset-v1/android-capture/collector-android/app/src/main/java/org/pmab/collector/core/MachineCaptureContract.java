package org.pmab.collector.core;

import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class MachineCaptureContract {
    private static final Set<String> HUMAN_DECISION_KEYS = new HashSet<>(Arrays.asList(
            "privacy_review_status",
            "gold_label",
            "gold_labels",
            "prediction",
            "predictions",
            "method_prediction",
            "paper_result_eligible"));

    private MachineCaptureContract() {}

    public static boolean containsHumanDecision(Object value) {
        if (value instanceof Map<?, ?>) {
            Map<?, ?> map = (Map<?, ?>) value;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (HUMAN_DECISION_KEYS.contains(String.valueOf(entry.getKey()))
                        || containsHumanDecision(entry.getValue())) {
                    return true;
                }
            }
        } else if (value instanceof List<?>) {
            for (Object child : (List<?>) value) {
                if (containsHumanDecision(child)) {
                    return true;
                }
            }
        }
        return false;
    }

    public static void requireMachineOnly(Map<String, Object> value) {
        if (containsHumanDecision(value)) {
            throw new IllegalArgumentException("machine capture cannot contain human decisions or predictions");
        }
    }
}
