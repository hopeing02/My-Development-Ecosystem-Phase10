package dev.mde.autoknowledge;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.atomic.AtomicReference;

public final class UnifiedCaptureRepositoryTest {
    @Test
    public void mapperKeepsDomainAndApiModelsSeparate() throws Exception {
        CaptureRequest request = request("cap_mapper_001");

        CaptureEnvelopeDto dto = new DefaultCaptureApiRequestMapper().map(request);
        JSONObject json = dto.toJson();

        assertEquals("1.0", json.getString("schemaVersion"));
        assertEquals("cap_mapper_001", json.getString("captureId"));
        assertEquals("codex", json.getString("sourceType"));
        assertEquals("clipboard_item", json.getString("captureType"));
        assertEquals("android", json.getString("captureDevice"));
        assertEquals("android_clipboard", json.getString("captureMethod"));
        assertEquals("codex_remote_android", json.getJSONObject("metadata").getString("sourceApp"));
        assertEquals(request.content, json.getJSONObject("payload").getString("content"));
    }

    @Test
    public void sharedNormalizationVectorsMatchAndroidImplementation() throws Exception {
        JSONArray vectors = resourceArray("normalization.json");
        ClipboardTextNormalizer normalizer = new ClipboardTextNormalizer();
        for (int index = 0; index < vectors.length(); index++) {
            JSONObject vector = vectors.getJSONObject(index);
            assertEquals(
                    vector.getString("name"),
                    vector.getString("normalized"),
                    normalizer.normalize(vector.getString("input"))
            );
        }
    }

    @Test
    public void sharedSensitiveHashAndFilenameVectorsMatchAndroidContract() throws Exception {
        SensitiveContentDetector detector = new SensitiveContentDetector();
        JSONArray sensitive = resourceArray("sensitive-content.json");
        for (int index = 0; index < sensitive.length(); index++) {
            JSONObject vector = sensitive.getJSONObject(index);
            assertEquals(
                    vector.getString("name"),
                    vector.getBoolean("sensitive"),
                    detector.containsSensitiveContent(vector.getString("input"))
            );
        }

        ClipboardTextNormalizer normalizer = new ClipboardTextNormalizer();
        ContentHashGenerator generator = new ContentHashGenerator();
        JSONArray hashes = resourceArray("hashes.json");
        for (int index = 0; index < hashes.length(); index++) {
            JSONObject vector = hashes.getJSONObject(index);
            String normalized = normalizer.normalize(vector.getString("input"));
            assertEquals(vector.getString("normalized"), normalized);
            assertEquals(vector.getString("sha256"), generator.sha256(normalized));
        }

        JSONArray filenames = resourceArray("filenames.json");
        for (int index = 0; index < filenames.length(); index++) {
            JSONObject vector = filenames.getJSONObject(index);
            String timestamp = OffsetDateTime.parse(vector.getString("capturedAt"))
                    .format(DateTimeFormatter.ofPattern("yyyy-MM-dd-HHmmss"));
            String filename = timestamp + "-" + vector.getString("sourceType")
                    + "-clip-" + vector.getString("contentHash").substring(0, 8) + ".md";
            assertEquals(vector.getString("filename"), filename);
        }
    }

    @Test
    public void unifiedRepositoryMapsSavedAndDuplicateResponses() throws Exception {
        try (StubServer saved = new StubServer(200, "{\"status\":\"saved\"}")) {
            CaptureResult result = repository(saved).saveCapture(request("cap_saved"));
            assertEquals(CaptureStatus.SAVED, result.status);
            assertTrue(saved.requestBody.get().contains("\"captureId\":\"cap_saved\""));
        }
        try (StubServer duplicate = new StubServer(200, "{\"status\":\"duplicate\"}")) {
            CaptureResult result = repository(duplicate).saveCapture(request("cap_duplicate"));
            assertEquals(CaptureStatus.DUPLICATE, result.status);
        }
    }

    @Test
    public void unifiedRepositoryDoesNotQueuePermanentClientErrors() throws Exception {
        try (StubServer sensitive = new StubServer(
                422,
                "{\"status\":\"error\",\"error\":{\"code\":\"SENSITIVE_CONTENT_DETECTED\"}}"
        )) {
            CaptureResult result = repository(sensitive).saveCapture(request("cap_sensitive"));
            assertEquals(CaptureStatus.BLOCKED_SENSITIVE, result.status);
        }
        try (StubServer invalid = new StubServer(
                422,
                "{\"status\":\"error\",\"error\":{\"code\":\"INVALID_PAYLOAD\"}}"
        )) {
            CaptureResult result = repository(invalid).saveCapture(request("cap_invalid"));
            assertEquals(CaptureStatus.FAILED, result.status);
        }
    }

    @Test
    public void unifiedRepositoryThrowsForTransientServerErrors() throws Exception {
        try (StubServer server = new StubServer(503, "{}")) {
            assertThrows(
                    IOException.class,
                    () -> repository(server).saveCapture(request("cap_retry"))
            );
        }
    }

    private static UnifiedCaptureRepository repository(StubServer server) {
        return new UnifiedCaptureRepository(
                server::url,
                new DefaultCaptureApiRequestMapper()
        );
    }

    private static JSONArray resourceArray(String name) throws Exception {
        try (InputStream input = UnifiedCaptureRepositoryTest.class
                .getClassLoader().getResourceAsStream(name)) {
            if (input == null) {
                throw new AssertionError(name + " resource is missing");
            }
            return new JSONArray(new String(input.readAllBytes(), StandardCharsets.UTF_8));
        }
    }

    private static CaptureRequest request(String captureId) {
        return new CaptureRequest(
                captureId,
                CaptureSource.CODEX,
                "Android 통합 저장소가 전송할 충분한 길이의 본문입니다.",
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "40_Reference",
                "ks-parent::Parent.md",
                "2026-08-02T21:20:00+09:00",
                "local-random-uuid"
        );
    }

    private static final class StubServer implements AutoCloseable {
        final ServerSocket server;
        final AtomicReference<String> requestBody = new AtomicReference<>("");
        final int status;
        final byte[] response;
        final Thread worker;

        StubServer(int status, String response) throws IOException {
            this.status = status;
            this.response = response.getBytes(StandardCharsets.UTF_8);
            server = new ServerSocket(0, 1);
            worker = new Thread(this::serveOne, "capture-api-test-server");
            worker.setDaemon(true);
            worker.start();
        }

        String url() {
            return "http://127.0.0.1:" + server.getLocalPort();
        }

        private void serveOne() {
            try (Socket socket = server.accept()) {
                InputStream input = socket.getInputStream();
                int contentLength = 0;
                String line;
                while (!(line = readLine(input)).isEmpty()) {
                    if (line.toLowerCase().startsWith("content-length:")) {
                        contentLength = Integer.parseInt(line.substring(15).trim());
                    }
                }
                requestBody.set(new String(input.readNBytes(contentLength), StandardCharsets.UTF_8));
                String reason = status >= 500 ? "Service Unavailable"
                        : status >= 400 ? "Unprocessable Content" : "OK";
                String headers = "HTTP/1.1 " + status + " " + reason + "\r\n"
                        + "Content-Type: application/json\r\n"
                        + "Content-Length: " + response.length + "\r\n"
                        + "Connection: close\r\n\r\n";
                OutputStream output = socket.getOutputStream();
                output.write(headers.getBytes(StandardCharsets.US_ASCII));
                output.write(response);
                output.flush();
            } catch (IOException ignored) {
                // Closing the test server interrupts an unused accept call.
            }
        }

        private static String readLine(InputStream input) throws IOException {
            StringBuilder line = new StringBuilder();
            int current;
            while ((current = input.read()) >= 0) {
                if (current == '\n') {
                    break;
                }
                if (current != '\r') {
                    line.append((char) current);
                }
            }
            return line.toString();
        }

        @Override
        public void close() throws IOException {
            server.close();
        }
    }
}
