package dev.mde.autoknowledge;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

final class ApiClient {
    private ApiClient() {}

    static void submit(String serverUrl, SharePayload payload) throws IOException, JSONException {
        URL endpoint = new URL(normalize(serverUrl) + "/v1/share");
        HttpURLConnection connection = (HttpURLConnection) endpoint.openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(10_000);
        connection.setReadTimeout(20_000);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        connection.setDoOutput(true);

        JSONObject body = new JSONObject()
                .put("content", payload.content)
                .put("target_folder", payload.targetFolder)
                .put("capture_origin", payload.captureOrigin);
        if (!payload.title.trim().isEmpty()) {
            body.put("title", payload.title);
        }
        if (!payload.sourceUrl.trim().isEmpty()) {
            body.put("source_url", payload.sourceUrl);
        }
        if (!payload.parentDocumentId.isEmpty()) {
            body.put("parent_document_id", payload.parentDocumentId);
        }
        if (!payload.sourceType.isEmpty()) {
            body.put("source_type", payload.sourceType);
        }
        if (!payload.sourceApp.isEmpty()) {
            body.put("source_app", payload.sourceApp);
        }
        if (!payload.contentHash.isEmpty()) {
            body.put("content_hash", payload.contentHash);
        }
        if (!payload.capturedAt.isEmpty()) {
            body.put("captured_at", payload.capturedAt);
        }
        if (!payload.deviceId.isEmpty()) {
            body.put("device_id", payload.deviceId);
        }
        byte[] encoded = body.toString().getBytes(StandardCharsets.UTF_8);
        try (OutputStream output = connection.getOutputStream()) {
            output.write(encoded);
        }

        int status = connection.getResponseCode();
        connection.disconnect();
        if (status != HttpURLConnection.HTTP_ACCEPTED) {
            throw new IOException("Server returned HTTP " + status);
        }
    }

    static List<KnowledgeDocumentCandidate> searchDocuments(
            String serverUrl,
            String query
    ) throws IOException, JSONException {
        String encodedQuery = URLEncoder.encode(query, StandardCharsets.UTF_8.name());
        URL endpoint = new URL(
                normalize(serverUrl) + "/v1/knowledge/documents?q=" + encodedQuery + "&limit=20"
        );
        HttpURLConnection connection = (HttpURLConnection) endpoint.openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(10_000);
        connection.setReadTimeout(30_000);
        connection.setRequestProperty("Accept", "application/json");

        int status = connection.getResponseCode();
        if (status != HttpURLConnection.HTTP_OK) {
            connection.disconnect();
            throw new IOException("Server returned HTTP " + status);
        }
        StringBuilder json = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8)
        )) {
            String line;
            while ((line = reader.readLine()) != null) {
                json.append(line);
            }
        } finally {
            connection.disconnect();
        }

        JSONArray documents = new JSONObject(json.toString()).getJSONArray("documents");
        List<KnowledgeDocumentCandidate> result = new ArrayList<>();
        for (int index = 0; index < documents.length(); index++) {
            JSONObject item = documents.getJSONObject(index);
            result.add(new KnowledgeDocumentCandidate(
                    item.getString("id"),
                    item.getString("title"),
                    item.getString("relative_path")
            ));
        }
        return result;
    }

    private static String normalize(String value) {
        return value.trim().replaceFirst("/+$", "");
    }
}
