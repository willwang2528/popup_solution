package org.pmab.collector;

import android.accessibilityservice.AccessibilityService;
import android.graphics.Rect;
import android.os.Build;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;
import org.pmab.collector.core.CanonicalEntry;
import org.pmab.collector.core.CanonicalStateHasher;

public final class AccessibilitySnapshotter {
    private static final int MAX_DEPTH = 100;
    private static final int MAX_NODES = 5_000;

    private final AccessibilityService service;

    public AccessibilitySnapshotter(AccessibilityService service) {
        this.service = service;
    }

    public Snapshot snapshot() throws Exception {
        long start = SystemClock.uptimeMillis();
        Accumulator accumulator = new Accumulator();
        JSONArray windowsJson = new JSONArray();

        List<AccessibilityWindowInfo> windows = new ArrayList<>(service.getWindows());
        windows.sort(Comparator.comparingInt(AccessibilityWindowInfo::getDisplayId)
                .thenComparingInt(AccessibilityWindowInfo::getLayer)
                .thenComparingInt(AccessibilityWindowInfo::getId));
        for (AccessibilityWindowInfo window : windows) {
            String windowId = "w:" + window.getDisplayId() + ":" + window.getId();
            JSONObject windowJson = new JSONObject();
            windowJson.put("id", windowId);
            windowJson.put("display_id", window.getDisplayId());
            windowJson.put("window_id", window.getId());
            windowJson.put("type", window.getType());
            windowJson.put("layer", window.getLayer());
            windowJson.put("title", nullable(window.getTitle()));
            windowJson.put("active", window.isActive());
            windowJson.put("focused", window.isFocused());
            windowJson.put("accessibility_focused", window.isAccessibilityFocused());
            Rect bounds = new Rect();
            window.getBoundsInScreen(bounds);
            windowJson.put("bounds_in_screen", bounds.flattenToString());

            List<String> windowChildren = new ArrayList<>();
            AccessibilityNodeInfo root = window.getRoot();
            if (root != null) {
                String rootId = windowId + "/n:0";
                windowChildren.add(rootId);
                windowJson.put("root", traverse(root, rootId, 0, accumulator));
            } else {
                windowJson.put("root", JSONObject.NULL);
            }
            Map<String, String> windowFields = new LinkedHashMap<>();
            windowFields.put("display_id", Integer.toString(window.getDisplayId()));
            windowFields.put("window_id", Integer.toString(window.getId()));
            windowFields.put("type", Integer.toString(window.getType()));
            windowFields.put("layer", Integer.toString(window.getLayer()));
            windowFields.put("title", stringOrNull(window.getTitle()));
            windowFields.put("active", Boolean.toString(window.isActive()));
            windowFields.put("focused", Boolean.toString(window.isFocused()));
            windowFields.put("accessibility_focused", Boolean.toString(window.isAccessibilityFocused()));
            windowFields.put("bounds_in_screen", bounds.flattenToString());
            accumulator.entries.add(new CanonicalEntry("window", windowId, windowFields, windowChildren));
            windowsJson.put(windowJson);
        }

        long end = SystemClock.uptimeMillis();
        String hash = CanonicalStateHasher.sha256(accumulator.entries);
        JSONObject json = new JSONObject();
        json.put("schema_version", "1.1");
        json.put("clock", "android.os.SystemClock.uptimeMillis");
        json.put("start_uptime_ms", start);
        json.put("end_uptime_ms", end);
        json.put("canonical_tree_sha256", hash);
        json.put("focus_token", accumulator.focusToken());
        json.put("node_count", accumulator.nodeCount);
        json.put("contains_sensitive_node", accumulator.containsSensitiveNode);
        json.put("truncated", accumulator.truncated);
        json.put("target_packages", new JSONArray(accumulator.packages));
        json.put("windows", windowsJson);
        return new Snapshot(
                start,
                end,
                hash,
                accumulator.focusToken(),
                accumulator.containsSensitiveNode,
                accumulator.truncated,
                accumulator.packages,
                json);
    }

    private JSONObject traverse(
            AccessibilityNodeInfo node,
            String nodeId,
            int depth,
            Accumulator accumulator) throws Exception {
        accumulator.nodeCount++;
        if (depth > MAX_DEPTH || accumulator.nodeCount > MAX_NODES) {
            accumulator.truncated = true;
            JSONObject truncated = new JSONObject();
            truncated.put("id", nodeId);
            truncated.put("truncated", true);
            return truncated;
        }

        boolean sensitive = node.isPassword()
                || (Build.VERSION.SDK_INT >= 34 && node.isAccessibilityDataSensitive());
        accumulator.containsSensitiveNode |= sensitive;
        String packageName = stringOrNull(node.getPackageName());
        if (packageName != null) {
            accumulator.packages.add(packageName);
        }

        Rect bounds = new Rect();
        node.getBoundsInScreen(bounds);
        List<Integer> actionIds = new ArrayList<>();
        for (AccessibilityNodeInfo.AccessibilityAction action : node.getActionList()) {
            actionIds.add(action.getId());
        }
        Collections.sort(actionIds);

        Map<String, String> fields = new LinkedHashMap<>();
        fields.put("window_id", Integer.toString(node.getWindowId()));
        fields.put("package", packageName);
        fields.put("class", stringOrNull(node.getClassName()));
        fields.put("view_id", node.getViewIdResourceName());
        fields.put("text", stringOrNull(node.getText()));
        fields.put("content_description", stringOrNull(node.getContentDescription()));
        fields.put("hint_text", stringOrNull(node.getHintText()));
        fields.put("state_description", stringOrNull(node.getStateDescription()));
        fields.put("pane_title", stringOrNull(node.getPaneTitle()));
        fields.put("tooltip_text", stringOrNull(node.getTooltipText()));
        fields.put("bounds_in_screen", bounds.flattenToString());
        fields.put("visible_to_user", Boolean.toString(node.isVisibleToUser()));
        fields.put("enabled", Boolean.toString(node.isEnabled()));
        fields.put("clickable", Boolean.toString(node.isClickable()));
        fields.put("long_clickable", Boolean.toString(node.isLongClickable()));
        fields.put("focusable", Boolean.toString(node.isFocusable()));
        fields.put("focused", Boolean.toString(node.isFocused()));
        fields.put("accessibility_focused", Boolean.toString(node.isAccessibilityFocused()));
        fields.put("checkable", Boolean.toString(node.isCheckable()));
        fields.put("checked", Boolean.toString(node.isChecked()));
        fields.put("selected", Boolean.toString(node.isSelected()));
        fields.put("scrollable", Boolean.toString(node.isScrollable()));
        fields.put("dismissable", Boolean.toString(node.isDismissable()));
        fields.put("heading", Boolean.toString(node.isHeading()));
        fields.put("password", Boolean.toString(node.isPassword()));
        fields.put("actions", joinIntegers(actionIds));

        JSONObject json = new JSONObject();
        json.put("id", nodeId);
        for (Map.Entry<String, String> field : fields.entrySet()) {
            json.put(field.getKey(), field.getValue() == null ? JSONObject.NULL : field.getValue());
        }
        JSONArray childrenJson = new JSONArray();
        List<String> childIds = new ArrayList<>();
        int childCount = node.getChildCount();
        for (int index = 0; index < childCount; index++) {
            AccessibilityNodeInfo child = node.getChild(index);
            String childId = nodeId + "." + index;
            childIds.add(childId);
            if (child == null) {
                accumulator.truncated = true;
                JSONObject missing = new JSONObject();
                missing.put("id", childId);
                missing.put("missing", true);
                childrenJson.put(missing);
            } else {
                childrenJson.put(traverse(child, childId, depth + 1, accumulator));
            }
        }
        json.put("children", childrenJson);
        accumulator.entries.add(new CanonicalEntry("node", nodeId, fields, childIds));
        if (node.isAccessibilityFocused() || node.isFocused()) {
            accumulator.focusTokens.add(
                    nodeId + ":a=" + node.isAccessibilityFocused() + ":i=" + node.isFocused());
        }
        return json;
    }

    private static Object nullable(CharSequence value) {
        return value == null ? JSONObject.NULL : value.toString();
    }

    private static String stringOrNull(CharSequence value) {
        return value == null ? null : value.toString();
    }

    private static String joinIntegers(List<Integer> values) {
        StringBuilder output = new StringBuilder();
        for (int index = 0; index < values.size(); index++) {
            if (index > 0) {
                output.append(',');
            }
            output.append(values.get(index));
        }
        return output.toString();
    }

    private static final class Accumulator {
        final List<CanonicalEntry> entries = new ArrayList<>();
        final Set<String> packages = new LinkedHashSet<>();
        final List<String> focusTokens = new ArrayList<>();
        int nodeCount;
        boolean containsSensitiveNode;
        boolean truncated;

        String focusToken() {
            Collections.sort(focusTokens);
            return focusTokens.isEmpty() ? "<none>" : String.join("|", focusTokens);
        }
    }

    public static final class Snapshot {
        private final long startUptimeMs;
        private final long endUptimeMs;
        private final String treeHash;
        private final String focusToken;
        private final boolean containsSensitiveNode;
        private final boolean truncated;
        private final Set<String> packages;
        private final JSONObject json;

        Snapshot(
                long startUptimeMs,
                long endUptimeMs,
                String treeHash,
                String focusToken,
                boolean containsSensitiveNode,
                boolean truncated,
                Set<String> packages,
                JSONObject json) {
            this.startUptimeMs = startUptimeMs;
            this.endUptimeMs = endUptimeMs;
            this.treeHash = treeHash;
            this.focusToken = focusToken;
            this.containsSensitiveNode = containsSensitiveNode;
            this.truncated = truncated;
            this.packages = Collections.unmodifiableSet(new LinkedHashSet<>(packages));
            this.json = json;
        }

        public long startUptimeMs() { return startUptimeMs; }
        public long endUptimeMs() { return endUptimeMs; }
        public String treeHash() { return treeHash; }
        public String focusToken() { return focusToken; }
        public boolean containsSensitiveNode() { return containsSensitiveNode; }
        public boolean truncated() { return truncated; }
        public boolean containsPackage(String packageName) { return packages.contains(packageName); }
        public JSONObject json() { return json; }
    }
}
