package org.pmab.collector;

import android.os.FileObserver;
import android.os.Handler;
import android.util.Log;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import org.json.JSONObject;
import org.pmab.collector.core.CaptureRequest;

final class CaptureRequestObserver extends FileObserver {
    private static final String TAG = "PmabRequestObserver";
    private static final long MAX_REQUEST_BYTES = 16_384;

    private final File directory;
    private final Handler worker;
    private final CaptureCoordinator coordinator;

    CaptureRequestObserver(File directory, Handler worker, CaptureCoordinator coordinator) {
        super(directory, FileObserver.MOVED_TO);
        this.directory = directory;
        this.worker = worker;
        this.coordinator = coordinator;
    }

    @Override
    public void onEvent(int event, String path) {
        if (path == null || !path.endsWith(".request") || path.contains("/")) {
            return;
        }
        worker.post(() -> consume(path));
    }

    private void consume(String path) {
        File requestFile = new File(directory, path);
        try {
            if (!requestFile.exists()) {
                return;
            }
            if (!requestFile.isFile() || Files.isSymbolicLink(requestFile.toPath())) {
                throw new IllegalArgumentException("request must be a regular app-private file");
            }
            long length = requestFile.length();
            if (length <= 0 || length > MAX_REQUEST_BYTES) {
                throw new IllegalArgumentException("request size outside bounds");
            }
            String text = new String(
                    Files.readAllBytes(requestFile.toPath()), StandardCharsets.UTF_8);
            JSONObject json = new JSONObject(text);
            Map<String, String> fields = new LinkedHashMap<>();
            Iterator<String> keys = json.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                Object value = json.get(key);
                if (!(value instanceof String)) {
                    throw new IllegalArgumentException("request values must be strings");
                }
                fields.put(key, (String) value);
            }
            coordinator.capture(CaptureRequest.from(fields));
        } catch (Exception error) {
            Log.e(TAG, "capture request rejected", error);
        } finally {
            if (!requestFile.delete()) {
                Log.w(TAG, "could not remove consumed request");
            }
        }
    }

    void scanPendingRequests() {
        File[] pending = directory.listFiles(
                file -> file.isFile()
                        && !Files.isSymbolicLink(file.toPath())
                        && file.getName().endsWith(".request")
                        && !file.getName().contains("/"));
        if (pending == null) {
            Log.w(TAG, "could not scan pending request directory");
            return;
        }
        Arrays.sort(pending, (left, right) -> left.getName().compareTo(right.getName()));
        for (File file : pending) {
            consume(file.getName());
        }
    }
}
