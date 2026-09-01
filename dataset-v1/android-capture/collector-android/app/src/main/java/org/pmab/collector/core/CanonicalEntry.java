package org.pmab.collector.core;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class CanonicalEntry {
    private final String kind;
    private final String id;
    private final Map<String, String> fields;
    private final List<String> orderedChildIds;

    public CanonicalEntry(
            String kind,
            String id,
            Map<String, String> fields,
            List<String> orderedChildIds) {
        if (kind == null || kind.isBlank() || id == null || id.isBlank()) {
            throw new IllegalArgumentException("canonical entry kind and id must be non-empty");
        }
        this.kind = kind;
        this.id = id;
        this.fields = Collections.unmodifiableMap(new LinkedHashMap<>(fields));
        this.orderedChildIds = Collections.unmodifiableList(new ArrayList<>(orderedChildIds));
    }

    public String kind() {
        return kind;
    }

    public String id() {
        return id;
    }

    public Map<String, String> fields() {
        return fields;
    }

    public List<String> orderedChildIds() {
        return orderedChildIds;
    }
}
