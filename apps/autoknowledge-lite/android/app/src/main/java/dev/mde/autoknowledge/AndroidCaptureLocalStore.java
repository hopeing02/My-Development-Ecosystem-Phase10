package dev.mde.autoknowledge;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

final class AndroidCaptureLocalStore implements CaptureLocalStore {
    private static final String PREFERENCES = "capture_local_store";
    private static final String RECENT_HASHES = "recent_hashes";
    private static final String PENDING = "pending_captures";
    private static final int MAX_RECENT_HASHES = 100;
    private final SharedPreferences preferences;
    private final SecureLocalTextStore secureTextStore = new SecureLocalTextStore();

    AndroidCaptureLocalStore(Context context) {
        preferences = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE);
    }

    @Override
    public synchronized boolean containsHash(String hash) {
        JSONArray recent = array(RECENT_HASHES);
        for (int index = 0; index < recent.length(); index++) {
            if (hash.equals(recent.optString(index))) {
                return true;
            }
        }
        JSONArray pending = array(PENDING);
        for (int index = 0; index < pending.length(); index++) {
            if (hash.equals(pending.optJSONObject(index).optString("contentHash"))) {
                return true;
            }
        }
        return false;
    }

    @Override
    public synchronized void recordHash(String hash) {
        JSONArray current = array(RECENT_HASHES);
        JSONArray updated = new JSONArray();
        updated.put(hash);
        for (int index = 0; index < current.length() && updated.length() < MAX_RECENT_HASHES; index++) {
            String existing = current.optString(index);
            if (!hash.equals(existing)) {
                updated.put(existing);
            }
        }
        preferences.edit().putString(RECENT_HASHES, updated.toString()).apply();
    }

    @Override
    public synchronized void enqueue(CaptureRequest request) throws Exception {
        JSONArray items = array(PENDING);
        for (int index = 0; index < items.length(); index++) {
            if (request.contentHash.equals(items.getJSONObject(index).optString("contentHash"))) {
                return;
            }
        }
        items.put(toJson(request));
        if (!preferences.edit().putString(PENDING, items.toString()).commit()) {
            throw new IllegalStateException("Unable to persist pending capture");
        }
    }

    @Override
    public synchronized List<CaptureRequest> pending() {
        List<CaptureRequest> result = new ArrayList<>();
        JSONArray items = array(PENDING);
        for (int index = 0; index < items.length(); index++) {
            try {
                result.add(fromJson(items.getJSONObject(index)));
            } catch (Exception ignored) {
                // Keep unreadable encrypted entries in storage for manual recovery.
            }
        }
        return result;
    }

    @Override
    public synchronized int retryCount(String hash) {
        JSONObject item = find(hash);
        return item == null ? 0 : item.optInt("retryCount", 0);
    }

    @Override
    public synchronized void markRetryFailed(String hash) {
        JSONArray items = array(PENDING);
        for (int index = 0; index < items.length(); index++) {
            JSONObject item = items.optJSONObject(index);
            if (item != null && hash.equals(item.optString("contentHash"))) {
                try {
                    item.put("retryCount", item.optInt("retryCount", 0) + 1);
                } catch (Exception ignored) {
                    return;
                }
            }
        }
        preferences.edit().putString(PENDING, items.toString()).apply();
    }

    @Override
    public synchronized void removePending(String hash) {
        JSONArray current = array(PENDING);
        JSONArray updated = new JSONArray();
        for (int index = 0; index < current.length(); index++) {
            JSONObject item = current.optJSONObject(index);
            if (item != null && !hash.equals(item.optString("contentHash"))) {
                updated.put(item);
            }
        }
        preferences.edit().putString(PENDING, updated.toString()).apply();
    }

    @Override
    public synchronized int pendingCount() {
        return array(PENDING).length();
    }

    private JSONObject toJson(CaptureRequest request) throws Exception {
        return new JSONObject()
                .put("source", request.source.name())
                .put("content", secureTextStore.encrypt(request.content))
                .put("contentHash", request.contentHash)
                .put("targetFolder", request.targetFolder)
                .put("parentDocumentId", request.parentDocumentId)
                .put("capturedAt", request.capturedAt)
                .put("deviceId", request.deviceId)
                .put("retryCount", 0);
    }

    private CaptureRequest fromJson(JSONObject item) throws Exception {
        return new CaptureRequest(
                CaptureSource.fromStored(item.optString("source")),
                secureTextStore.decrypt(item.getString("content")),
                item.getString("contentHash"),
                item.optString("targetFolder", SharePayload.DEFAULT_VAULT_FOLDER),
                item.optString("parentDocumentId"),
                item.optString("capturedAt"),
                item.optString("deviceId")
        );
    }

    private JSONObject find(String hash) {
        JSONArray items = array(PENDING);
        for (int index = 0; index < items.length(); index++) {
            JSONObject item = items.optJSONObject(index);
            if (item != null && hash.equals(item.optString("contentHash"))) {
                return item;
            }
        }
        return null;
    }

    private JSONArray array(String key) {
        try {
            return new JSONArray(preferences.getString(key, "[]"));
        } catch (Exception error) {
            return new JSONArray();
        }
    }
}
