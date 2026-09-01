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
}
