package dev.mde.autoknowledge;

import android.app.Activity;
import android.os.Bundle;
import android.text.InputType;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity {
    static final String PREFERENCES = "autoknowledge";
    static final String SERVER_URL = "server_url";

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

        setContentView(layout);
    }
}
