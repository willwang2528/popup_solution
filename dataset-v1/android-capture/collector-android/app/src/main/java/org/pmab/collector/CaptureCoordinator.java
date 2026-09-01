package org.pmab.collector;

import android.accessibilityservice.AccessibilityService;
import android.graphics.Bitmap;
import android.hardware.HardwareBuffer;
import android.os.Handler;
import android.os.SystemClock;
import android.util.Log;
import android.view.Display;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.util.concurrent.Executor;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.LongSupplier;
import org.pmab.collector.core.CaptureRequest;
import org.pmab.collector.core.CaptureTimingGate;
import org.pmab.collector.core.TimingDecision;
import org.pmab.collector.core.TimingEvidence;

public final class CaptureCoordinator {
    private static final String TAG = "PmabCapture";
    private static final long MAXIMUM_BRACKET_DISTANCE_MS = 3_000;

    private final AccessibilityService service;
    private final LongSupplier eventSequence;
    private final Handler worker;
    private final Executor callbackExecutor;
    private final AccessibilitySnapshotter snapshotter;
    private final AtomicBundleWriter writer;
    private final AtomicBoolean inFlight = new AtomicBoolean();

    public CaptureCoordinator(
            AccessibilityService service,
            LongSupplier eventSequence,
            Handler worker,
            File filesDirectory) {
        this.service = service;
        this.eventSequence = eventSequence;
        this.worker = worker;
        this.callbackExecutor = command -> worker.post(command);
        this.snapshotter = new AccessibilitySnapshotter(service);
        this.writer = new AtomicBundleWriter(service, filesDirectory);
    }

    public void capture(CaptureRequest request) {
        if (!inFlight.compareAndSet(false, true)) {
            reject(request, "capture_already_in_flight");
            return;
        }
        try {
            AccessibilitySnapshotter.Snapshot before = snapshotter.snapshot();
            long sequenceBefore = eventSequence.getAsLong();
            if (before.containsSensitiveNode()) {
                rejectAndRelease(request, "sensitive_accessibility_node_present");
                return;
            }
            if (before.truncated()) {
                rejectAndRelease(request, "accessibility_tree_incomplete");
                return;
            }
            if (!before.containsPackage(request.expectedTargetPackage())) {
                rejectAndRelease(request, "expected_target_package_absent");
                return;
            }

            long requestUptime = SystemClock.uptimeMillis();
            service.takeScreenshot(
                    Display.DEFAULT_DISPLAY,
                    callbackExecutor,
                    new AccessibilityService.TakeScreenshotCallback() {
                        @Override
                        public void onSuccess(AccessibilityService.ScreenshotResult result) {
                            handleScreenshotSuccess(
                                    request, before, sequenceBefore, requestUptime, result);
                        }

                        @Override
                        public void onFailure(int errorCode) {
                            rejectAndRelease(request, "screenshot_error_" + errorCode);
                        }
                    });
        } catch (Exception error) {
            Log.e(TAG, "capture failed before screenshot", error);
            rejectAndRelease(request, "pre_screenshot_exception");
        }
    }

    private void handleScreenshotSuccess(
            CaptureRequest request,
            AccessibilitySnapshotter.Snapshot before,
            long sequenceBefore,
            long requestUptime,
            AccessibilityService.ScreenshotResult result) {
        HardwareBuffer buffer = result.getHardwareBuffer();
        try {
            long callbackUptime = SystemClock.uptimeMillis();
            Bitmap hardwareBitmap = Bitmap.wrapHardwareBuffer(buffer, result.getColorSpace());
            if (hardwareBitmap == null) {
                rejectAndRelease(request, "hardware_buffer_wrap_failed");
                return;
            }
            Bitmap softwareBitmap = hardwareBitmap.copy(Bitmap.Config.ARGB_8888, false);
            if (softwareBitmap == null) {
                rejectAndRelease(request, "software_bitmap_copy_failed");
                return;
            }
            ByteArrayOutputStream png = new ByteArrayOutputStream();
            if (!softwareBitmap.compress(Bitmap.CompressFormat.PNG, 100, png)) {
                rejectAndRelease(request, "png_encoding_failed");
                return;
            }
            int screenshotWidthPx = softwareBitmap.getWidth();
            int screenshotHeightPx = softwareBitmap.getHeight();
            softwareBitmap.recycle();

            AccessibilitySnapshotter.Snapshot after = snapshotter.snapshot();
            long sequenceAfter = eventSequence.getAsLong();
            if (after.containsSensitiveNode()) {
                rejectAndRelease(request, "sensitive_accessibility_node_present");
                return;
            }
            if (after.truncated()) {
                rejectAndRelease(request, "accessibility_tree_incomplete");
                return;
            }
            TimingEvidence timing = new TimingEvidence(
                    before.startUptimeMs(),
                    before.endUptimeMs(),
                    requestUptime,
                    result.getTimestamp(),
                    callbackUptime,
                    after.startUptimeMs(),
                    after.endUptimeMs(),
                    before.treeHash(),
                    after.treeHash(),
                    sequenceBefore,
                    sequenceAfter,
                    before.focusToken(),
                    after.focusToken());
            TimingDecision decision =
                    CaptureTimingGate.evaluate(timing, MAXIMUM_BRACKET_DISTANCE_MS);
            if (!decision.accepted()) {
                rejectAndRelease(request, decision.reason());
                return;
            }
            writer.writeComplete(
                    request,
                    before,
                    after,
                    png.toByteArray(),
                    timing,
                    decision,
                    service.getServiceInfo(),
                    screenshotWidthPx,
                    screenshotHeightPx);
        } catch (Exception error) {
            Log.e(TAG, "capture failed after screenshot", error);
            reject(request, "post_screenshot_exception");
        } finally {
            buffer.close();
            inFlight.set(false);
        }
    }

    private void rejectAndRelease(CaptureRequest request, String reason) {
        try {
            reject(request, reason);
        } finally {
            inFlight.set(false);
        }
    }

    private void reject(CaptureRequest request, String reason) {
        try {
            writer.writeRejected(request, reason, service.getServiceInfo());
        } catch (Exception error) {
            Log.e(TAG, "could not persist rejected capture", error);
        }
    }
}
