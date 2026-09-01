package org.pmab.collector.core;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public final class CanonicalStateHasher {
    private CanonicalStateHasher() {}

    public static String sha256(List<CanonicalEntry> entries) {
        byte[] bytes = canonicalize(entries).getBytes(StandardCharsets.UTF_8);
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(bytes);
            StringBuilder hex = new StringBuilder(digest.length * 2);
            for (byte value : digest) {
                hex.append(String.format("%02x", value & 0xff));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 is required", error);
        }
    }

    static String canonicalize(List<CanonicalEntry> entries) {
        List<CanonicalEntry> ordered = new ArrayList<>(entries);
        ordered.sort(Comparator.comparing(CanonicalEntry::kind).thenComparing(CanonicalEntry::id));
        StringBuilder output = new StringBuilder();
        for (CanonicalEntry entry : ordered) {
            append(output, "entry-kind", entry.kind());
            append(output, "entry-id", entry.id());
            for (Map.Entry<String, String> field : new TreeMap<>(entry.fields()).entrySet()) {
                append(output, "field-key", field.getKey());
                append(output, "field-value", field.getValue() == null ? "<null>" : field.getValue());
            }
            for (String childId : entry.orderedChildIds()) {
                append(output, "child", childId);
            }
            output.append("entry-end\n");
        }
        return output.toString();
    }

    private static void append(StringBuilder output, String label, String value) {
        String safe = value == null ? "<null>" : value;
        output.append(label)
                .append(':')
                .append(safe.getBytes(StandardCharsets.UTF_8).length)
                .append(':')
                .append(safe)
                .append('\n');
    }
}
