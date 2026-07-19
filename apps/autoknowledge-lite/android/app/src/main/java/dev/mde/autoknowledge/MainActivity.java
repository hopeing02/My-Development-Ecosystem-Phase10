package dev.mde.autoknowledge;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.os.Bundle;
import android.text.InputType;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    static final String PREFERENCES = "autoknowledge";
    static final String SERVER_URL = "server_url";
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        int padding = (int) (24 * getResources().getDisplayMetrics().density);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(padding, padding, padding, padding);

        TextView heading = new TextView(this);
        heading.setText("AutoKnowledge Lite");
        heading.setTextSize(24);
        layout.addView(heading);

        TextView help = new TextView(this);
        help.setText("PC에서 실행 중인 서버 주소를 입력하세요. 예: http://192.168.0.10:8000");
        help.setTextSize(16);
        help.setPadding(0, padding, 0, padding / 2);
        layout.addView(help);

        EditText serverUrl = new EditText(this);
        serverUrl.setHint("http://192.168.0.10:8000");
        serverUrl.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        serverUrl.setText(getSharedPreferences(PREFERENCES, MODE_PRIVATE).getString(SERVER_URL, ""));
        layout.addView(serverUrl, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        Button save = new Button(this);
        save.setText("서버 주소 저장");
        save.setOnClickListener(view -> {
            String value = serverUrl.getText().toString().trim();
            if (!value.startsWith("http://") && !value.startsWith("https://")) {
                Toast.makeText(this, "http:// 또는 https://로 시작해야 합니다.", Toast.LENGTH_LONG).show();
                return;
            }
            getSharedPreferences(PREFERENCES, MODE_PRIVATE).edit().putString(SERVER_URL, value).apply();
            Toast.makeText(this, "저장했습니다. 이제 다른 앱의 공유 메뉴에서 AutoKnowledge Lite를 선택하세요.", Toast.LENGTH_LONG).show();
        });
        layout.addView(save);

        TextView clipboardHelp = new TextView(this);
        clipboardHelp.setText("채팅이나 문서의 전체 내용을 복사한 뒤 아래 버튼을 누르면 잘리지 않은 텍스트를 저장합니다.");
        clipboardHelp.setTextSize(16);
        clipboardHelp.setPadding(0, padding, 0, padding / 2);
        layout.addView(clipboardHelp);

        Button saveClipboard = new Button(this);
        saveClipboard.setText("클립보드 내용 저장");
        saveClipboard.setOnClickListener(view -> submitClipboard(saveClipboard));
        layout.addView(saveClipboard);

        setContentView(layout);
    }

    private void submitClipboard(Button button) {
        ClipboardManager clipboard =
                (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        ClipData clip = clipboard.getPrimaryClip();
        if (clip == null || clip.getItemCount() == 0) {
            Toast.makeText(this, "클립보드에 텍스트가 없습니다.", Toast.LENGTH_LONG).show();
            return;
        }
        CharSequence text = clip.getItemAt(0).coerceToText(this);
        SharePayload payload = SharePayload.fromClipboard(text);
        if (!payload.isValid()) {
            Toast.makeText(this, "클립보드에 텍스트가 없습니다.", Toast.LENGTH_LONG).show();
            return;
        }
        String serverUrl = getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                .getString(SERVER_URL, "");
        if (serverUrl.trim().isEmpty()) {
            Toast.makeText(this, "먼저 서버 주소를 저장하세요.", Toast.LENGTH_LONG).show();
            return;
        }

        button.setEnabled(false);
        button.setText("전송 중…");
        executor.execute(() -> {
            try {
                ApiClient.submit(serverUrl, payload);
                runOnUiThread(() -> finishClipboardSubmit(
                        button, "클립보드 내용을 AutoKnowledge에 저장했습니다."));
            } catch (Exception error) {
                runOnUiThread(() -> finishClipboardSubmit(
                        button, "전송하지 못했습니다. 서버 주소와 실행 상태를 확인하세요."));
            }
        });
    }

    private void finishClipboardSubmit(Button button, String message) {
        button.setEnabled(true);
        button.setText("클립보드 내용 저장");
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }
}
