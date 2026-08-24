package dev.mde.knowledgeviewer;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;

final class ServerAddress {
    private ServerAddress() {
    }

    static String normalize(String value) {
        String candidate = value == null ? "" : value.trim();
        try {
            URI uri = new URI(candidate);
            String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
            if (!(scheme.equals("http") || scheme.equals("https"))) {
                throw new IllegalArgumentException("http:// 또는 https://로 시작해야 합니다.");
            }
            if (uri.getHost() == null || uri.getRawUserInfo() != null) {
                throw new IllegalArgumentException("올바른 서버 주소를 입력하세요.");
            }
            String path = uri.getRawPath();
            if ((path != null && !path.isEmpty() && !path.equals("/"))
                    || uri.getRawQuery() != null
                    || uri.getRawFragment() != null) {
                throw new IllegalArgumentException("서버 주소에는 경로, 쿼리 또는 조각을 넣을 수 없습니다.");
            }
            return scheme + "://" + uri.getRawAuthority();
        } catch (URISyntaxException error) {
            throw new IllegalArgumentException("올바른 서버 주소를 입력하세요.", error);
        }
    }

    static boolean sameOrigin(String baseUrl, String targetUrl) {
        try {
            URI base = new URI(normalize(baseUrl));
            URI target = new URI(targetUrl);
            return base.getScheme().equalsIgnoreCase(target.getScheme())
                    && base.getHost().equalsIgnoreCase(target.getHost())
                    && effectivePort(base) == effectivePort(target);
        } catch (IllegalArgumentException | URISyntaxException error) {
            return false;
        }
    }

    private static int effectivePort(URI uri) {
        if (uri.getPort() >= 0) {
            return uri.getPort();
        }
        return "https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80;
    }
}
