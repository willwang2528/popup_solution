package org.pmab.collector;

import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.Context;
import android.content.pm.PackageInfo;
import android.os.Build;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.Map;
import org.json.JSONObject;
import org.pmab.collector.BuildConfig;
import org.pmab.collector.core.CaptureRequest;
import org.pmab.collector.core.TimingDecision;
import org.pmab.collector.core.TimingEvidence;

final class AtomicBundleWriter {
    private final Context context;
    private final File bundleRoot;

    AtomicBundleWriter(Context context, File filesDirectory) {
        this.context = context;
        bundleRoot = new File(filesDirectory, "capture_bundles");
        if (!bundleRoot.exists() && !bundleRoot.mkdirs()) {
            throw new IllegalStateException("cannot create app-private bundle directory");
        }
    }

    void writeComplete(
            CaptureRequest request,
            AccessibilitySnapshotter.Snapshot before,
            AccessibilitySnapshotter.Snapshot after,
            byte[] screenshotPng,
            TimingEvidence timing,
            TimingDecision decision,
            AccessibilityServiceInfo serviceInfo,
            int screenshotWidthPx,
            int screenshotHeightPx) throws Exception {
        File partial = preparePartial(request);
        writeBytes(new File(partial, "tree-before.json"), before.json().toString(2).getBytes(StandardCharsets.UTF_8));
        writeBytes(new File(partial, "tree-after.json"), after.json().toString(2).getBytes(StandardCharsets.UTF_8));
        writeBytes(new File(partial, "screenshot.png"), screenshotPng);

        JSONObject machine = baseMachineRecord(
                request,
                "complete",
                decision.reason(),
                serviceInfo,
                screenshotWidthPx,
                screenshotHeightPx);
        machine.put("timing", timingJson(timing));
        JSONObject artifacts = new JSONObject();
        addArtifact(artifacts, partial, "tree_before", "tree-before.json");
        addArtifact(artifacts, partial, "tree_after", "tree-after.json");
        addArtifact(artifacts, partial, "screenshot", "screenshot.png");
        machine.put("artifacts", artifacts);
        writeBytes(
                new File(partial, "machine-capture.json"),
                machine.toString(2).getBytes(StandardCharsets.UTF_8));
        publish(partial, request.captureId());
    }

    void writeRejected(
            CaptureRequest request,
            String reason,
            AccessibilityServiceInfo serviceInfo) throws Exception {
        File partial = preparePartial(request);
        JSONObject machine = baseMachineRecord(
                request,
                "rejected",
                reason,
                serviceInfo,
                context.getResources().getDisplayMetrics().widthPixels,
                context.getResources().getDisplayMetrics().heightPixels);
        machine.put("artifacts", new JSONObject());
        writeBytes(
                new File(partial, "machine-capture.json"),
                machine.toString(2).getBytes(StandardCharsets.UTF_8));
        publish(partial, request.captureId());
    }

    private File preparePartial(CaptureRequest request) {
        File destination = new File(bundleRoot, request.captureId());
        if (destination.exists()) {
            throw new IllegalStateException("capture id already exists");
        }
        File partial = new File(
                bundleRoot,
                request.captureId() + ".partial-" + request.requestNonce());
        if (partial.exists() || !partial.mkdir()) {
            throw new IllegalStateException("cannot create partial capture bundle");
        }
        return partial;
    }

    private void publish(File partial, String captureId) {
        File destination = new File(bundleRoot, captureId);
        if (!partial.renameTo(destination)) {
            throw new IllegalStateException("cannot atomically publish capture bundle");
        }
    }

    private JSONObject baseMachineRecord(
            CaptureRequest request,
            String status,
            String reason,
            AccessibilityServiceInfo serviceInfo,
            int displayWidthPx,
            int displayHeightPx) throws Exception {
        JSONObject machine = new JSONObject();
        machine.put("schema_version", "1.1");
        machine.put("collector", "pmab-android-accessibilityservice");
        machine.put("machine_status", status);
        machine.put("machine_reason", reason);
        machine.put("clock", "android.os.SystemClock.uptimeMillis");
        machine.put("request", new JSONObject(request.fields()));
        JSONObject runtime = new JSONObject();
        runtime.put("sdk_int", Build.VERSION.SDK_INT);
        runtime.put("build_fingerprint", Build.FINGERPRINT);
        runtime.put("source_revision", BuildConfig.SOURCE_REVISION);
        runtime.put("service_capabilities", serviceInfo.getCapabilities());
        runtime.put("service_flags", serviceInfo.flags);
        runtime.put("service_event_types", serviceInfo.eventTypes);
        runtime.put("service_feedback_type", serviceInfo.feedbackType);
        JSONObject device = new JSONObject();
        device.put("manufacturer", Build.MANUFACTURER);
        device.put("model", Build.MODEL);
        device.put("android_release", Build.VERSION.RELEASE);
        device.put("display_width_px", displayWidthPx);
        device.put("display_height_px", displayHeightPx);
        runtime.put("device", device);
        runtime.put("target_app", packageRecord(request.expectedTargetPackage()));
        runtime.put("collector_app", packageRecord(context.getPackageName()));
        runtime.put("locale", Locale.getDefault().toLanguageTag());
        machine.put("runtime", runtime);
        return machine;
    }

    private JSONObject packageRecord(String packageName) throws Exception {
        PackageInfo packageInfo = context.getPackageManager().getPackageInfo(packageName, 0);
        JSONObject record = new JSONObject();
        record.put("package_name", packageName);
        record.put("version_name", packageInfo.versionName == null ? "<unknown>" : packageInfo.versionName);
        record.put("version_code", packageInfo.getLongVersionCode());
        return record;
    }

    private static JSONObject timingJson(TimingEvidence timing) throws Exception {
        JSONObject json = new JSONObject();
        json.put("tree_before_start_uptime_ms", timing.treeBeforeStartUptimeMs());
        json.put("tree_before_end_uptime_ms", timing.treeBeforeEndUptimeMs());
        json.put("screenshot_request_uptime_ms", timing.screenshotRequestUptimeMs());
        json.put("screenshot_result_uptime_ms", timing.screenshotResultUptimeMs());
        json.put("screenshot_callback_uptime_ms", timing.screenshotCallbackUptimeMs());
        json.put("tree_after_start_uptime_ms", timing.treeAfterStartUptimeMs());
        json.put("tree_after_end_uptime_ms", timing.treeAfterEndUptimeMs());
        json.put("tree_before_sha256", timing.beforeTreeHash());
        json.put("tree_after_sha256", timing.afterTreeHash());
        json.put("event_sequence_before", timing.eventSequenceBefore());
        json.put("event_sequence_after", timing.eventSequenceAfter());
        json.put("focus_token_before", timing.focusTokenBefore());
        json.put("focus_token_after", timing.focusTokenAfter());
        return json;
    }

    private static void addArtifact(
            JSONObject artifacts,
            File directory,
            String key,
            String filename) throws Exception {
        File file = new File(directory, filename);
        JSONObject record = new JSONObject();
        record.put("filename", filename);
        record.put("bytes", file.length());
        record.put("sha256", sha256(file));
        artifacts.put(key, record);
    }

    private static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] bytes = java.nio.file.Files.readAllBytes(file.toPath());
        byte[] hash = digest.digest(bytes);
        StringBuilder hex = new StringBuilder(hash.length * 2);
        for (byte value : hash) {
            hex.append(String.format("%02x", value & 0xff));
        }
        return hex.toString();
    }

    private static void writeBytes(File file, byte[] bytes) throws Exception {
        try (FileOutputStream output = new FileOutputStream(file, false)) {
            output.write(bytes);
            output.flush();
            output.getFD().sync();
        }
    }
}
