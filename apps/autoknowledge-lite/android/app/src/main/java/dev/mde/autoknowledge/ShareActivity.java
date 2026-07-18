package dev.mde.autoknowledge;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.widget.TextView;
import android.widget.Toast;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class ShareActivity extends Activity {
    private final ExecutorService executor = Executors.newSingleThreadExecutor();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        TextView status = new TextView(this);
        status.setText("AutoKnowledge로 보내는 중…");
        status.setTextSize(18);
        int padding = (int) (32 * getResources().getDisplayMetrics().density);
        status.setPadding(padding, padding, padding, padding);
        setContentView(status);

        Intent intent = getIntent();
        SharePayload payload = SharePayload.from(
                intent.getCharSequenceExtra(Intent.EXTRA_SUBJECT),
                intent.getCharSequenceExtra(Intent.EXTRA_TEXT));
        String serverUrl = getSharedPreferences(MainActivity.PREFERENCES, MODE_PRIVATE)
                .getString(MainActivity.SERVER_URL, "");

        if (!Intent.ACTION_SEND.equals(intent.getAction()) || !payload.isValid()) {
            finishWithMessage("공유된 텍스트가 없습니다.");
            return;
        }
        if (serverUrl.trim().isEmpty()) {
            finishWithMessage("먼저 AutoKnowledge Lite 앱에서 서버 주소를 저장하세요.");
            return;
        }

        executor.execute(() -> {
            try {
                ApiClient.submit(serverUrl, payload);
                runOnUiThread(() -> finishWithMessage("AutoKnowledge에 저장했습니다."));
            } catch (Exception error) {
                runOnUiThread(() -> finishWithMessage("전송하지 못했습니다. 서버 주소와 실행 상태를 확인하세요."));
            }
        });
    }

    private void finishWithMessage(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
        finish();
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }
}
