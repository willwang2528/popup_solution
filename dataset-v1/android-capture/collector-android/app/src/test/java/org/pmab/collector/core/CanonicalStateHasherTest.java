package org.pmab.collector.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotEquals;

import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.Test;

public final class CanonicalStateHasherTest {
    private static CanonicalEntry entry(String id, String text, List<String> children) {
        Map<String, String> fields = new LinkedHashMap<>();
        fields.put("text", text);
        fields.put("class", "android.widget.TextView");
        return new CanonicalEntry("node", id, fields, children);
    }

    @Test
    public void mapAndEntryInsertionOrderCannotChangeStateCommitment() {
        // Break caught: serializer iteration order creates different state tokens for one tree.
        CanonicalEntry first = entry("n1", "message", Collections.singletonList("n2"));
        CanonicalEntry second = entry("n2", "OK", Collections.emptyList());

        String forward = CanonicalStateHasher.sha256(Arrays.asList(first, second));
        String reverse = CanonicalStateHasher.sha256(Arrays.asList(second, first));

        assertEquals(forward, reverse);
    }

    @Test
    public void semanticTextOrChildOrderChangeMustChangeStateCommitment() {
        // Break caught: a popup message or reading-order change is treated as a stable state.
        CanonicalEntry baseline = entry("n1", "amount: 10", Arrays.asList("n2", "n3"));
        CanonicalEntry changedText = entry("n1", "amount: 100", Arrays.asList("n2", "n3"));
        CanonicalEntry changedOrder = entry("n1", "amount: 10", Arrays.asList("n3", "n2"));

        String baselineHash = CanonicalStateHasher.sha256(Collections.singletonList(baseline));

        assertNotEquals(baselineHash, CanonicalStateHasher.sha256(Collections.singletonList(changedText)));
        assertNotEquals(baselineHash, CanonicalStateHasher.sha256(Collections.singletonList(changedOrder)));
    }

    @Test
    public void nullAndLiteralNullSentinelMustNotCollide() {
        // Break caught: a missing accessibility value can be replaced by visible "<null>" text.
        CanonicalEntry missing = entry("n1", null, Collections.emptyList());
        CanonicalEntry literal = entry("n1", "<null>", Collections.emptyList());

        assertNotEquals(
                CanonicalStateHasher.sha256(Collections.singletonList(missing)),
                CanonicalStateHasher.sha256(Collections.singletonList(literal)));
    }

    @Test
    public void sharedOfflineFinalizerGoldenVectorRemainsStable() {
        // Break caught: Android and the offline finalizer disagree about the committed tree.
        Map<String, String> rootFields = collectorNodeFields(null, false, "");
        Map<String, String> messageFields = collectorNodeFields(
                "Private collector fixture message", true, "1");
        Map<String, String> windowFields = new LinkedHashMap<>();
        windowFields.put("display_id", "0");
        windowFields.put("window_id", "7");
        windowFields.put("type", "1");
        windowFields.put("layer", "0");
        windowFields.put("title", null);
        windowFields.put("active", "true");
        windowFields.put("focused", "true");
        windowFields.put("accessibility_focused", "true");
        windowFields.put("bounds_in_screen", "[0,0][3,2]");

        List<CanonicalEntry> entries = Arrays.asList(
                new CanonicalEntry(
                        "window", "w:0:7", windowFields,
                        Collections.singletonList("w:0:7/n:0")),
                new CanonicalEntry(
                        "node", "w:0:7/n:0", rootFields,
                        Collections.singletonList("w:0:7/n:0.0")),
                new CanonicalEntry(
                        "node", "w:0:7/n:0.0", messageFields,
                        Collections.emptyList()));

        assertEquals(
                "9053372116a0bb6ae09ec860dbcfcc58744ce4ffc55e9d45c838ec9b8e0c9867",
                CanonicalStateHasher.sha256(entries));
    }

    private static Map<String, String> collectorNodeFields(
            String text, boolean accessibilityFocused, String actions) {
        Map<String, String> fields = new LinkedHashMap<>();
        fields.put("window_id", "7");
        fields.put("package", "org.example.fixture");
        fields.put("class", "android.widget.TextView");
        fields.put("view_id", "org.example.fixture:id/message");
        fields.put("text", text);
        fields.put("content_description", null);
        fields.put("hint_text", null);
        fields.put("state_description", null);
        fields.put("pane_title", null);
        fields.put("tooltip_text", null);
        fields.put("bounds_in_screen", "[0,0][3,2]");
        fields.put("visible_to_user", "true");
        fields.put("enabled", "true");
        fields.put("clickable", "false");
        fields.put("long_clickable", "false");
        fields.put("focusable", "true");
        fields.put("focused", "false");
        fields.put("accessibility_focused", Boolean.toString(accessibilityFocused));
        fields.put("checkable", "false");
        fields.put("checked", "false");
        fields.put("selected", "false");
        fields.put("scrollable", "false");
        fields.put("dismissable", "false");
        fields.put("heading", "false");
        fields.put("password", "false");
        fields.put("actions", actions);
        return fields;
    }
}
