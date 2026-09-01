package org.pmab.collector;

import android.accessibilityservice.AccessibilityService;
import android.os.Handler;
import android.os.HandlerThread;
import android.view.accessibility.AccessibilityEvent;
import java.io.File;
import java.util.concurrent.atomic.AtomicLong;

public final class PmabCaptureService extends AccessibilityService {
    private static final long PENDING_REQUEST_SCAN_INTERVAL_MS = 2_000;
    private final AtomicLong eventSequence = new AtomicLong();
    private HandlerThread workerThread;
    private Handler worker;
    private CaptureRequestObserver requestObserver;
    private final Runnable pendingRequestScan = new Runnable() {
        @Override
        public void run() {
            if (requestObserver != null && worker != null) {
                requestObserver.scanPendingRequests();
                worker.postDelayed(this, PENDING_REQUEST_SCAN_INTERVAL_MS);
            }
        }
    };

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        workerThread = new HandlerThread("pmab-capture-worker");
        workerThread.start();
        worker = new Handler(workerThread.getLooper());

        File requestDirectory = new File(getFilesDir(), "capture_requests");
        if (!requestDirectory.exists() && !requestDirectory.mkdirs()) {
            throw new IllegalStateException("cannot create app-private request directory");
        }
        CaptureCoordinator coordinator =
                new CaptureCoordinator(this, eventSequence::get, worker, getFilesDir());
        requestObserver = new CaptureRequestObserver(requestDirectory, worker, coordinator);
        requestObserver.startWatching();
        worker.post(pendingRequestScan);
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        eventSequence.incrementAndGet();
    }

    @Override
    public void onInterrupt() {
        eventSequence.incrementAndGet();
    }

    @Override
    public void onDestroy() {
        if (requestObserver != null) {
            requestObserver.stopWatching();
        }
        if (worker != null) {
            worker.removeCallbacks(pendingRequestScan);
        }
        if (workerThread != null) {
            workerThread.quitSafely();
        }
        super.onDestroy();
    }
}
