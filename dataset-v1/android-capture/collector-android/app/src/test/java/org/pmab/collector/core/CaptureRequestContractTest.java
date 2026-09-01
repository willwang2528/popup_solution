package org.pmab.collector.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.Test;

public final class CaptureRequestContractTest {
    @Test
    public void acceptsOnlyBoundedMachineTriggerFields() {
        // Break caught: request files become a route for gold labels or arbitrary host data.
        Map<String, String> request = validRequest();
        CaptureRequest validated = CaptureRequest.from(request);
        assertEquals("PMAB-A-CAP-001", validated.captureId());
        assertEquals("org.example.target", validated.expectedTargetPackage());

        request.put("gold_label", "popup");
        assertThrows(IllegalArgumentException.class, () -> CaptureRequest.from(request));
    }

    @Test
    public void rejectsMissingUnsafeOrPathLikeIdentifiers() {
        Map<String, String> missingNonce = validRequest();
        missingNonce.remove("request_nonce");
        assertThrows(IllegalArgumentException.class, () -> CaptureRequest.from(missingNonce));

        Map<String, String> pathLikeId = validRequest();
        pathLikeId.put("capture_id", "../escape");
        assertThrows(IllegalArgumentException.class, () -> CaptureRequest.from(pathLikeId));

        Map<String, String> emptyPackage = validRequest();
        emptyPackage.put("expected_target_package", "");
        assertThrows(IllegalArgumentException.class, () -> CaptureRequest.from(emptyPackage));
    }

    private static Map<String, String> validRequest() {
        Map<String, String> request = new LinkedHashMap<>();
        request.put("schema_version", "1.1");
        request.put("capture_id", "PMAB-A-CAP-001");
        request.put("item_id", "PMAB-0001");
        request.put("source_group_id", "SG-001");
        request.put("popup_template_family_id", "PF-dialog");
        request.put("intended_stratum", "no_popup_candidate");
        request.put("expected_target_package", "org.example.target");
        request.put("request_nonce", "bd33d879debc4c38");
        return request;
    }
}
