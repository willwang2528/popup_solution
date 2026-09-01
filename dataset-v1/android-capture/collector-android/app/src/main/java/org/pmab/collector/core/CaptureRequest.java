package org.pmab.collector.core;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

public final class CaptureRequest {
    private static final Set<String> REQUIRED_KEYS = Set.of(
            "schema_version",
            "capture_id",
            "item_id",
            "source_group_id",
            "popup_template_family_id",
            "intended_stratum",
            "expected_target_package",
            "request_nonce");
    private static final Pattern SAFE_IDENTIFIER =
            Pattern.compile("[A-Za-z0-9][A-Za-z0-9._:-]{0,127}");
    private static final Pattern PACKAGE_NAME =
            Pattern.compile("[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z][A-Za-z0-9_]*)+");
    private static final Pattern NONCE = Pattern.compile("[A-Fa-f0-9]{16,64}");

    private final Map<String, String> fields;

    private CaptureRequest(Map<String, String> fields) {
        this.fields = Collections.unmodifiableMap(new LinkedHashMap<>(fields));
    }

    public static CaptureRequest from(Map<String, String> candidate) {
        if (candidate == null || !candidate.keySet().equals(REQUIRED_KEYS)) {
            throw new IllegalArgumentException("capture request must contain exactly the V1.1 keys");
        }
        if (!"1.1".equals(candidate.get("schema_version"))) {
            throw new IllegalArgumentException("unsupported request schema");
        }
        for (String key : new String[] {
            "capture_id", "item_id", "source_group_id", "popup_template_family_id"
        }) {
            requireMatch(key, candidate.get(key), SAFE_IDENTIFIER);
        }
        String stratum = candidate.get("intended_stratum");
        if (!Set.of(
                "popup_candidate", "no_popup_candidate", "boundary_candidate").contains(stratum)) {
            throw new IllegalArgumentException("intended_stratum is outside the frozen V1 strata");
        }
        requireMatch("expected_target_package", candidate.get("expected_target_package"), PACKAGE_NAME);
        requireMatch("request_nonce", candidate.get("request_nonce"), NONCE);
        return new CaptureRequest(candidate);
    }

    private static void requireMatch(String key, String value, Pattern pattern) {
        if (value == null || !pattern.matcher(value).matches()) {
            throw new IllegalArgumentException("invalid " + key);
        }
    }

    public Map<String, String> fields() { return fields; }
    public String captureId() { return fields.get("capture_id"); }
    public String expectedTargetPackage() { return fields.get("expected_target_package"); }
    public String requestNonce() { return fields.get("request_nonce"); }
}
