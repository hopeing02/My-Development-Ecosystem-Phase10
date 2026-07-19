package dev.mde.autoknowledge;

import org.json.JSONObject;
import org.json.JSONException;

import java.io.IOException;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

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

        JSONObject body = new JSONObject().put("content", payload.content);
        if (!payload.title.trim().isEmpty()) {
            body.put("title", payload.title);
        }
        if (!payload.sourceUrl.trim().isEmpty()) {
            body.put("source_url", payload.sourceUrl);
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

    private static String normalize(String value) {
        return value.trim().replaceFirst("/+$", "");
    }
}
