package dev.mde.knowledgeviewer;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.ViewGroup;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    private static final String PREFERENCES = "mde_knowledge_viewer";
    private static final String SERVER_URL = "server_url";

    private EditText serverInput;
    private TextView status;
    private WebView webView;
    private String activeServer = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildLayout();
        configureWebView();

        String saved = getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                .getString(SERVER_URL, "");
        serverInput.setText(saved);
        if (!saved.isBlank()) {
            connect(saved);
        } else {
            status.setText("PC의 Knowledge Viewer 서버 주소를 입력하세요.");
        }
    }

    private void buildLayout() {
        float density = getResources().getDisplayMetrics().density;
        int padding = (int) (10 * density);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(238, 242, 249));

        LinearLayout controls = new LinearLayout(this);
        controls.setOrientation(LinearLayout.HORIZONTAL);
        controls.setPadding(padding, padding, padding, padding / 2);

        serverInput = new EditText(this);
        serverInput.setSingleLine(true);
        serverInput.setHint("http://PC-IP:8765");
        controls.addView(serverInput, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

        Button connect = new Button(this);
        connect.setText("연결");
        connect.setOnClickListener(view -> connect(serverInput.getText().toString()));
        controls.addView(connect);
        root.addView(controls);

        status = new TextView(this);
        status.setPadding(padding, 0, padding, padding / 2);
        status.setTextColor(Color.rgb(86, 97, 125));
        root.addView(status);

        webView = new WebView(this);
        root.addView(webView, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1
        ));
        setContentView(root);
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false);
        settings.setSaveFormData(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String target = request.getUrl().toString();
                if (ServerAddress.sameOrigin(activeServer, target)) {
                    return false;
                }
                Toast.makeText(MainActivity.this, "외부 주소 이동을 차단했습니다.", Toast.LENGTH_LONG).show();
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                status.setText("연결됨 · " + activeServer);
            }
        });
    }

    private void connect(String value) {
        try {
            activeServer = ServerAddress.normalize(value);
        } catch (IllegalArgumentException error) {
            Toast.makeText(this, error.getMessage(), Toast.LENGTH_LONG).show();
            return;
        }
        serverInput.setText(activeServer);
        getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                .edit()
                .putString(SERVER_URL, activeServer)
                .apply();
        status.setText("연결 중…");
        webView.loadUrl(activeServer + "/");
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        webView.stopLoading();
        webView.loadUrl("about:blank");
        webView.clearHistory();
        webView.clearCache(true);
        webView.destroy();
        super.onDestroy();
    }
}
