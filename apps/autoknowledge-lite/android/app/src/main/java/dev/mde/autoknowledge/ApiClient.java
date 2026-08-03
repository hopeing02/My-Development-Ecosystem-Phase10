package dev.mde.autoknowledge;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.InputStream;
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

    static CaptureResult submitCapture(
            String serverUrl,
            CaptureEnvelopeDto payload,
            String contentHash
    ) throws IOException, JSONException {
        URL endpoint = new URL(normalize(serverUrl) + "/api/v1/captures");
        HttpURLConnection connection = (HttpURLConnection) endpoint.openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(10_000);
        connection.setReadTimeout(20_000);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        connection.setRequestProperty("Accept", "application/json");
        connection.setDoOutput(true);

        byte[] encoded = payload.toJson().toString().getBytes(StandardCharsets.UTF_8);
        try (OutputStream output = connection.getOutputStream()) {
            output.write(encoded);
        }

        int status = connection.getResponseCode();
        String responseBody;
        try {
            responseBody = readBody(
                    status >= 400 ? connection.getErrorStream() : connection.getInputStream()
            );
        } finally {
            connection.disconnect();
        }
        if (status >= 500) {
            throw new IOException("Server returned HTTP " + status);
        }
        JSONObject response = responseBody.isEmpty()
                ? new JSONObject()
                : new JSONObject(responseBody);
        if (status >= 400) {
            JSONObject error = response.optJSONObject("error");
            String code = error == null ? "" : error.optString("code");
            if ("SENSITIVE_CONTENT_DETECTED".equals(code)) {
                return new CaptureResult(CaptureStatus.BLOCKED_SENSITIVE, contentHash);
            }
            return new CaptureResult(CaptureStatus.FAILED, contentHash);
        }
        String responseStatus = response.optString("status");
        if ("duplicate".equals(responseStatus)) {
            return new CaptureResult(CaptureStatus.DUPLICATE, contentHash);
        }
        if ("saved".equals(responseStatus)) {
            return new CaptureResult(CaptureStatus.SAVED, contentHash);
        }
        throw new IOException("Server returned an invalid capture response");
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

    static boolean checkCodexConnection(String serverUrl, String apiKey)
            throws IOException, JSONException {
        return "connected".equals(requestJson(
                serverUrl,
                "/api/v1/mobile/status",
                "GET",
                apiKey,
                null
        ).optString("status"));
    }

    static List<CodexProject> listCodexProjects(String serverUrl, String apiKey)
            throws IOException, JSONException {
        JSONArray items = requestJson(
                serverUrl,
                "/api/v1/mobile/codex/projects",
                "GET",
                apiKey,
                null
        ).getJSONArray("projects");
        List<CodexProject> result = new ArrayList<>();
        for (int index = 0; index < items.length(); index++) {
            result.add(CodexProject.fromJson(items.getJSONObject(index)));
        }
        return result;
    }

    static List<CodexSessionSummary> listCodexSessions(String serverUrl, String apiKey)
            throws IOException, JSONException {
        JSONArray items = requestJson(
                serverUrl,
                "/api/v1/mobile/codex/sessions?limit=20",
                "GET",
                apiKey,
                null
        ).getJSONArray("sessions");
        List<CodexSessionSummary> result = new ArrayList<>();
        for (int index = 0; index < items.length(); index++) {
            result.add(CodexSessionSummary.fromJson(items.getJSONObject(index)));
        }
        return result;
    }

    static String startCodexCapture(
            String serverUrl,
            String apiKey,
            String projectId,
            String title
    ) throws IOException, JSONException {
        JSONObject response = requestJson(
                serverUrl,
                "/api/v1/mobile/codex/captures",
                "POST",
                apiKey,
                new JSONObject().put("projectId", projectId).put("title", title)
        );
        return response.getString("captureSessionId");
    }

    static void attachCodexSession(
            String serverUrl,
            String apiKey,
            String captureSessionId,
            String sourceSessionId,
            boolean consent
    ) throws IOException, JSONException {
        requestJson(
                serverUrl,
                "/api/v1/mobile/codex/captures/" + encodePath(captureSessionId) + "/attach",
                "POST",
                apiKey,
                new JSONObject().put("sourceSessionId", sourceSessionId).put("consent", consent)
        );
    }

    static CodexCaptureStatus syncCodexSession(
            String serverUrl,
            String apiKey,
            String captureSessionId
    ) throws IOException, JSONException {
        return CodexCaptureStatus.fromJson(requestJson(
                serverUrl,
                "/api/v1/mobile/codex/captures/" + encodePath(captureSessionId) + "/sync",
                "POST",
                apiKey,
                new JSONObject().put("transmit", true)
        ));
    }

    static CodexCaptureStatus finalizeCodexSession(
            String serverUrl,
            String apiKey,
            String captureSessionId
    ) throws IOException, JSONException {
        return CodexCaptureStatus.fromJson(requestJson(
                serverUrl,
                "/api/v1/mobile/codex/captures/" + encodePath(captureSessionId) + "/finalize",
                "POST",
                apiKey,
                new JSONObject().put("transmit", true)
        ));
    }

    static CodexCaptureStatus codexCaptureStatus(
            String serverUrl,
            String apiKey,
            String captureSessionId
    ) throws IOException, JSONException {
        return CodexCaptureStatus.fromJson(requestJson(
                serverUrl,
                "/api/v1/mobile/codex/captures/" + encodePath(captureSessionId),
                "GET",
                apiKey,
                null
        ));
    }

    private static JSONObject requestJson(
            String serverUrl,
            String path,
            String method,
            String apiKey,
            JSONObject body
    ) throws IOException, JSONException {
        HttpURLConnection connection = (HttpURLConnection) new URL(normalize(serverUrl) + path)
                .openConnection();
        connection.setRequestMethod(method);
        connection.setConnectTimeout(10_000);
        connection.setReadTimeout(30_000);
        connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("Authorization", "Bearer " + apiKey);
        if (body != null) {
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setDoOutput(true);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body.toString().getBytes(StandardCharsets.UTF_8));
            }
        }
        int status = connection.getResponseCode();
        String responseBody;
        try {
            responseBody = readBody(status >= 400 ? connection.getErrorStream() : connection.getInputStream());
        } finally {
            connection.disconnect();
        }
        JSONObject response = responseBody.isEmpty() ? new JSONObject() : new JSONObject(responseBody);
        if (status >= 400) {
            JSONObject error = response.optJSONObject("error");
            String code = error == null ? "HTTP_" + status : error.optString("code", "HTTP_" + status);
            throw new IOException("Codex control failed: " + code);
        }
        return response;
    }

    private static String encodePath(String value) throws IOException {
        return URLEncoder.encode(value, StandardCharsets.UTF_8.name()).replace("+", "%20");
    }

    private static String normalize(String value) {
        return value.trim().replaceFirst("/+$", "");
    }

    private static String readBody(InputStream input) throws IOException {
        if (input == null) {
            return "";
        }
        StringBuilder body = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(input, StandardCharsets.UTF_8)
        )) {
            String line;
            while ((line = reader.readLine()) != null) {
                body.append(line);
            }
        }
        return body.toString();
    }
}
