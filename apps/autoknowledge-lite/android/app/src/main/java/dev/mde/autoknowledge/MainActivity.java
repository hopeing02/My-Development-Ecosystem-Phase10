package dev.mde.autoknowledge;

import android.app.Activity;
import android.app.AlertDialog;
import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.text.InputType;
import android.text.method.PasswordTransformationMethod;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    static final String PREFERENCES = "autoknowledge";
    static final String SERVER_URL = "server_url";
    static final String VAULT_FOLDER = "vault_folder";
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final ExecutorService codexExecutor = Executors.newSingleThreadExecutor();
    private String selectedParentDocumentId = "";
    private TextView selectedParentText;
    private Button clearParentButton;
    private CaptureDependencies captureDependencies;
    private TextView autoCaptureStatus;
    private TextView pendingStatus;
    private Switch autoCaptureSwitch;
    private CodexSessionSummary selectedCodexSession;
    private TextView selectedCodexSessionText;
    private TextView codexCaptureStatusText;
    private Spinner codexProjectSpinner;
    private String knowledgeViewerUrl = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        captureDependencies = new CaptureDependencies(this);
        selectedParentDocumentId = captureDependencies.settings.parentDocumentId();
        requestNotificationPermission();
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
        serverUrl.setText(getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                .getString(SERVER_URL, ""));
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
            getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                    .edit()
                    .putString(SERVER_URL, value)
                    .apply();
            executor.execute(() -> captureDependencies.retryUseCase.execute(false));
            Toast.makeText(
                    this,
                    "저장했습니다. 이제 다른 앱의 공유 메뉴에서 AutoKnowledge Lite를 선택하세요.",
                    Toast.LENGTH_LONG
            ).show();
        });
        layout.addView(save);

        TextView folderLabel = new TextView(this);
        folderLabel.setText("개인 Vault 저장 폴더");
        folderLabel.setTextSize(16);
        folderLabel.setPadding(0, padding, 0, padding / 2);
        layout.addView(folderLabel);

        Spinner folderSpinner = new Spinner(this);
        ArrayAdapter<String> folderAdapter = new ArrayAdapter<>(
                this,
                android.R.layout.simple_spinner_item,
                SharePayload.VAULT_FOLDERS
        );
        folderAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        folderSpinner.setAdapter(folderAdapter);
        String savedFolder = getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                .getString(VAULT_FOLDER, SharePayload.DEFAULT_VAULT_FOLDER);
        folderSpinner.setSelection(SharePayload.folderIndex(savedFolder));
        folderSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(
                    AdapterView<?> parent,
                    View view,
                    int position,
                    long id
            ) {
                getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                        .edit()
                        .putString(VAULT_FOLDER, SharePayload.VAULT_FOLDERS[position])
                        .apply();
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
                getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                        .edit()
                        .putString(VAULT_FOLDER, SharePayload.DEFAULT_VAULT_FOLDER)
                        .apply();
            }
        });
        layout.addView(folderSpinner);

        TextView parentLabel = new TextView(this);
        parentLabel.setText("이 문서를 참조할 상위 주제 문서 (선택)");
        parentLabel.setTextSize(16);
        parentLabel.setPadding(0, padding, 0, padding / 2);
        layout.addView(parentLabel);

        EditText parentSearch = new EditText(this);
        parentSearch.setHint("제목·별칭·경로로 기존 문서 검색");
        parentSearch.setSingleLine(true);
        layout.addView(parentSearch, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        Button searchParent = new Button(this);
        searchParent.setText("상위 주제 검색");
        searchParent.setOnClickListener(view -> searchParentDocuments(
                searchParent,
                parentSearch.getText().toString()
        ));
        layout.addView(searchParent);

        selectedParentText = new TextView(this);
        selectedParentText.setText(defaultParentMessage());
        selectedParentText.setTextSize(14);
        selectedParentText.setPadding(0, padding / 2, 0, 0);
        layout.addView(selectedParentText);

        clearParentButton = new Button(this);
        clearParentButton.setText("상위 주제 선택 해제");
        clearParentButton.setVisibility(View.GONE);
        clearParentButton.setOnClickListener(view -> clearParentSelection());
        layout.addView(clearParentButton);

        TextView sourceLabel = new TextView(this);
        sourceLabel.setText("저장 출처");
        sourceLabel.setTextSize(16);
        sourceLabel.setPadding(0, padding, 0, padding / 2);
        layout.addView(sourceLabel);

        Spinner sourceSpinner = new Spinner(this);
        String[] sourceNames = {
                CaptureSource.CHATGPT.displayName,
                CaptureSource.CODEX.displayName,
                CaptureSource.GENERAL.displayName
        };
        ArrayAdapter<String> sourceAdapter = new ArrayAdapter<>(
                this,
                android.R.layout.simple_spinner_item,
                sourceNames
        );
        sourceAdapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        sourceSpinner.setAdapter(sourceAdapter);
        sourceSpinner.setSelection(captureDependencies.settings.source().ordinal());
        sourceSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                captureDependencies.settings.setSource(CaptureSource.values()[position]);
                refreshAutoCaptureUi();
                refreshRunningService();
            }

            @Override
            public void onNothingSelected(AdapterView<?> parent) {
                captureDependencies.settings.setSource(CaptureSource.CHATGPT);
            }
        });
        layout.addView(sourceSpinner);

        autoCaptureSwitch = new Switch(this);
        autoCaptureSwitch.setText("AI 대화 클립보드 자동 저장");
        autoCaptureSwitch.setPadding(0, padding, 0, padding / 2);
        autoCaptureSwitch.setChecked(
                captureDependencies.settings.state() != AutoCaptureState.DISABLED
        );
        autoCaptureSwitch.setOnCheckedChangeListener((button, enabled) -> {
            if (enabled) {
                enableAutoCapture();
            } else {
                disableAutoCapture();
            }
        });
        layout.addView(autoCaptureSwitch);

        TextView privacyNotice = new TextView(this);
        privacyNotice.setText(
                "자동 저장이 켜진 동안 복사한 텍스트가 저장될 수 있습니다. "
                        + "비밀번호나 개인정보를 복사하기 전 자동 저장을 일시 중지하세요."
        );
        layout.addView(privacyNotice);

        autoCaptureStatus = new TextView(this);
        autoCaptureStatus.setPadding(0, padding / 2, 0, padding / 2);
        layout.addView(autoCaptureStatus);

        pendingStatus = new TextView(this);
        layout.addView(pendingStatus);

        Button retryPending = new Button(this);
        retryPending.setText("다시 전송");
        retryPending.setOnClickListener(view -> {
            retryPending.setEnabled(false);
            executor.execute(() -> {
                int saved = captureDependencies.retryUseCase.execute(true);
                runOnUiThread(() -> {
                    retryPending.setEnabled(true);
                    refreshAutoCaptureUi();
                    Toast.makeText(
                            this,
                            saved + "건을 다시 전송했습니다.",
                            Toast.LENGTH_LONG
                    ).show();
                });
            });
        });
        layout.addView(retryPending);

        TextView clipboardHelp = new TextView(this);
        clipboardHelp.setText("채팅이나 문서의 전체 내용을 복사한 뒤 아래 버튼을 누르면 선택한 폴더에 저장합니다.");
        clipboardHelp.setTextSize(16);
        clipboardHelp.setPadding(0, padding, 0, padding / 2);
        layout.addView(clipboardHelp);

        Button saveClipboard = new Button(this);
        saveClipboard.setText("클립보드 내용 저장");
        saveClipboard.setOnClickListener(view -> submitClipboard(
                saveClipboard,
                (String) folderSpinner.getSelectedItem()
        ));
        layout.addView(saveClipboard);

        buildCodexCaptureSection(layout, padding, serverUrl);

        ScrollView scrollView = new ScrollView(this);
        scrollView.addView(layout);
        setContentView(scrollView);
        restoreParentSelection();
        refreshAutoCaptureUi();
        executor.execute(() -> captureDependencies.retryUseCase.execute(false));
        if (captureDependencies.settings.state() != AutoCaptureState.DISABLED) {
            refreshRunningService();
        }
    }

    private void buildCodexCaptureSection(LinearLayout layout, int padding, EditText serverUrl) {
        TextView heading = new TextView(this);
        heading.setText("Codex 전체 공개 대화 저장");
        heading.setTextSize(20);
        heading.setPadding(0, padding * 2, 0, padding / 2);
        layout.addView(heading);

        TextView notice = new TextView(this);
        notice.setText(
                "모바일은 Codex 파일이나 App Server에 직접 접근하지 않습니다. "
                        + "인증된 PC 수집기에는 공개 사용자·assistant 응답과 공개 도구 기록의 저장만 요청합니다."
        );
        layout.addView(notice);

        EditText controlKey = new EditText(this);
        controlKey.setHint("모바일 제어 API 키");
        controlKey.setSingleLine(true);
        controlKey.setTransformationMethod(PasswordTransformationMethod.getInstance());
        controlKey.setText(captureDependencies.settings.controlApiKey());
        layout.addView(controlKey, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        Button checkConnection = new Button(this);
        checkConnection.setText("PC 연결 상태 확인");
        checkConnection.setOnClickListener(view -> {
            String key = controlKey.getText().toString().trim();
            String url = serverUrl.getText().toString().trim();
            if (url.isEmpty() || key.isEmpty()) {
                Toast.makeText(this, "서버 주소와 제어 API 키를 입력하세요.", Toast.LENGTH_LONG).show();
                return;
            }
            captureDependencies.settings.setControlApiKey(key);
            checkConnection.setEnabled(false);
            codexExecutor.execute(() -> {
                try {
                    boolean connected = ApiClient.checkCodexConnection(url, key);
                    runOnUiThread(() -> {
                        checkConnection.setEnabled(true);
                        codexCaptureStatusText.setText(connected ? "PC 수집기에 연결되었습니다." : "PC 수집기를 사용할 수 없습니다.");
                    });
                } catch (Exception error) {
                    runOnUiThread(() -> {
                        checkConnection.setEnabled(true);
                        codexCaptureStatusText.setText("PC 연결 실패 — 서버 주소, API 키와 Tailscale 연결을 확인하세요.");
                    });
                }
            });
        });
        layout.addView(checkConnection);

        codexProjectSpinner = new Spinner(this);
        layout.addView(codexProjectSpinner);

        Button recentSessions = new Button(this);
        recentSessions.setText("최근 실제 Codex 세션 조회");
        recentSessions.setOnClickListener(view -> loadCodexSessions(recentSessions));
        layout.addView(recentSessions);

        selectedCodexSessionText = new TextView(this);
        selectedCodexSessionText.setText("저장할 Codex 세션을 선택하지 않았습니다.");
        selectedCodexSessionText.setPadding(0, padding / 2, 0, padding / 2);
        layout.addView(selectedCodexSessionText);

        Switch consent = new Switch(this);
        consent.setText("전체 공개 대화 수집에 동의합니다");
        layout.addView(consent);

        Button attachAndSync = new Button(this);
        attachAndSync.setText("선택 세션 연결 및 지금 수집");
        attachAndSync.setOnClickListener(view -> attachAndSyncCodexSession(attachAndSync, consent));
        layout.addView(attachAndSync);

        Button syncMore = new Button(this);
        syncMore.setText("추가 대화 동기화");
        syncMore.setOnClickListener(view -> syncExistingCodexSession(syncMore));
        layout.addView(syncMore);

        Button finalize = new Button(this);
        finalize.setText("Finalize 및 저장");
        finalize.setOnClickListener(view -> finalizeCodexSession(finalize));
        layout.addView(finalize);

        codexCaptureStatusText = new TextView(this);
        codexCaptureStatusText.setText("Codex 저장 상태: 대기");
        codexCaptureStatusText.setPadding(0, padding / 2, 0, padding / 2);
        layout.addView(codexCaptureStatusText);

        Button openViewer = new Button(this);
        openViewer.setText("Knowledge Viewer에서 열기");
        openViewer.setOnClickListener(view -> openKnowledgeViewer());
        layout.addView(openViewer);

        knowledgeViewerUrl = captureDependencies.settings.knowledgeViewerUrl();
        String savedCapture = captureDependencies.settings.codexCaptureSessionId();
        if (!savedCapture.isEmpty()) {
            codexCaptureStatusText.setText("이전 Codex capture session: " + savedCapture);
        }
    }

    private void loadCodexSessions(Button button) {
        String url = captureDependencies.settings.serverUrl();
        String key = captureDependencies.settings.controlApiKey();
        if (url.isEmpty() || key.isEmpty()) {
            Toast.makeText(this, "서버 주소와 제어 API 키를 먼저 저장하세요.", Toast.LENGTH_LONG).show();
            return;
        }
        button.setEnabled(false);
        codexCaptureStatusText.setText("최근 Codex 세션을 조회 중입니다…");
        codexExecutor.execute(() -> {
            try {
                List<CodexProject> projects = ApiClient.listCodexProjects(url, key);
                List<CodexSessionSummary> sessions = ApiClient.listCodexSessions(url, key);
                runOnUiThread(() -> {
                    button.setEnabled(true);
                    codexProjectSpinner.setAdapter(new ArrayAdapter<>(
                            this,
                            android.R.layout.simple_spinner_dropdown_item,
                            projects
                    ));
                    showCodexSessions(sessions);
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    button.setEnabled(true);
                    codexCaptureStatusText.setText("Codex 세션 목록을 조회하지 못했습니다.");
                });
            }
        });
    }

    private void showCodexSessions(List<CodexSessionSummary> sessions) {
        if (sessions.isEmpty()) {
            codexCaptureStatusText.setText("조회 가능한 공개 Codex 세션이 없습니다.");
            return;
        }
        String[] labels = new String[sessions.size()];
        for (int index = 0; index < sessions.size(); index++) {
            labels[index] = sessions.get(index).label();
        }
        new AlertDialog.Builder(this)
                .setTitle("저장할 실제 Codex 세션")
                .setItems(labels, (dialog, index) -> {
                    selectedCodexSession = sessions.get(index);
                    selectedCodexSessionText.setText(selectedCodexSession.label());
                    codexCaptureStatusText.setText("세션을 선택했습니다. 전체 공개 대화 수집에 동의한 뒤 연결하세요.");
                })
                .setNegativeButton("취소", null)
                .show();
    }

    private void attachAndSyncCodexSession(Button button, Switch consent) {
        Object selectedProject = codexProjectSpinner.getSelectedItem();
        if (selectedCodexSession == null || !(selectedProject instanceof CodexProject)) {
            Toast.makeText(this, "Codex 세션과 등록 프로젝트를 선택하세요.", Toast.LENGTH_LONG).show();
            return;
        }
        if (!consent.isChecked()) {
            Toast.makeText(this, "전체 공개 대화 수집 동의가 필요합니다.", Toast.LENGTH_LONG).show();
            return;
        }
        String url = captureDependencies.settings.serverUrl();
        String key = captureDependencies.settings.controlApiKey();
        CodexProject project = (CodexProject) selectedProject;
        button.setEnabled(false);
        codexCaptureStatusText.setText("MDE capture session을 만들고 공개 대화를 수집 중입니다…");
        codexExecutor.execute(() -> {
            try {
                String captureId = ApiClient.startCodexCapture(
                        url,
                        key,
                        project.projectId,
                        selectedCodexSession.title
                );
                ApiClient.attachCodexSession(
                        url,
                        key,
                        captureId,
                        selectedCodexSession.sourceSessionId,
                        true
                );
                CodexCaptureStatus result = ApiClient.syncCodexSession(url, key, captureId);
                captureDependencies.settings.setCodexCaptureSessionId(captureId);
                runOnUiThread(() -> {
                    button.setEnabled(true);
                    codexCaptureStatusText.setText(result.label() + " · finalize 전");
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    button.setEnabled(true);
                    codexCaptureStatusText.setText("Codex 대화 수집에 실패했습니다. 기존 클립보드 저장은 계속 사용할 수 있습니다.");
                });
            }
        });
    }

    private void syncExistingCodexSession(Button button) {
        runCodexCaptureAction(button, false);
    }

    private void finalizeCodexSession(Button button) {
        runCodexCaptureAction(button, true);
    }

    private void runCodexCaptureAction(Button button, boolean finalize) {
        String captureId = captureDependencies.settings.codexCaptureSessionId();
        if (captureId.isEmpty()) {
            Toast.makeText(this, "먼저 Codex 세션을 연결하세요.", Toast.LENGTH_LONG).show();
            return;
        }
        button.setEnabled(false);
        codexCaptureStatusText.setText(finalize ? "Finalize 및 저장 중입니다…" : "추가 공개 대화를 동기화 중입니다…");
        codexExecutor.execute(() -> {
            try {
                CodexCaptureStatus result = finalize
                        ? ApiClient.finalizeCodexSession(
                                captureDependencies.settings.serverUrl(),
                                captureDependencies.settings.controlApiKey(),
                                captureId
                        )
                        : ApiClient.syncCodexSession(
                                captureDependencies.settings.serverUrl(),
                                captureDependencies.settings.controlApiKey(),
                                captureId
                        );
                if (!result.viewerUrl.isEmpty()) {
                    knowledgeViewerUrl = result.viewerUrl;
                    captureDependencies.settings.setKnowledgeViewerUrl(result.viewerUrl);
                }
                runOnUiThread(() -> {
                    button.setEnabled(true);
                    codexCaptureStatusText.setText(result.label());
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    button.setEnabled(true);
                    codexCaptureStatusText.setText("Codex 저장 작업에 실패했습니다. 다시 시도할 수 있습니다.");
                });
            }
        });
    }

    private void openKnowledgeViewer() {
        if (knowledgeViewerUrl.isEmpty()) {
            Toast.makeText(this, "저장 완료 응답에 Knowledge Viewer 주소가 없습니다.", Toast.LENGTH_LONG).show();
            return;
        }
        startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(knowledgeViewerUrl)));
    }

    private void searchParentDocuments(Button button, String rawQuery) {
        String query = rawQuery.trim();
        if (query.isEmpty()) {
            Toast.makeText(this, "검색어를 입력하세요.", Toast.LENGTH_LONG).show();
            return;
        }
        String serverUrl = getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                .getString(SERVER_URL, "");
        if (serverUrl.trim().isEmpty()) {
            Toast.makeText(this, "먼저 서버 주소를 저장하세요.", Toast.LENGTH_LONG).show();
            return;
        }
        button.setEnabled(false);
        button.setText("검색 중…");
        executor.execute(() -> {
            try {
                List<KnowledgeDocumentCandidate> candidates =
                        ApiClient.searchDocuments(serverUrl, query);
                runOnUiThread(() -> {
                    button.setEnabled(true);
                    button.setText("상위 주제 검색");
                    showParentCandidates(candidates);
                });
            } catch (Exception error) {
                runOnUiThread(() -> {
                    button.setEnabled(true);
                    button.setText("상위 주제 검색");
                    Toast.makeText(
                            this,
                            "문서를 검색하지 못했습니다. 서버 상태를 확인하세요.",
                            Toast.LENGTH_LONG
                    ).show();
                });
            }
        });
    }

    private void showParentCandidates(List<KnowledgeDocumentCandidate> candidates) {
        if (candidates.isEmpty()) {
            Toast.makeText(this, "검색 결과가 없습니다.", Toast.LENGTH_LONG).show();
            return;
        }
        String[] labels = new String[candidates.size()];
        for (int index = 0; index < candidates.size(); index++) {
            labels[index] = candidates.get(index).label();
        }
        new AlertDialog.Builder(this)
                .setTitle("상위 주제 문서 선택")
                .setItems(labels, (dialog, index) -> selectParent(candidates.get(index)))
                .setNegativeButton("취소", null)
                .show();
    }

    private void selectParent(KnowledgeDocumentCandidate candidate) {
        selectedParentDocumentId = candidate.id;
        String label = candidate.title + "\n" + candidate.relativePath;
        captureDependencies.settings.setParentDocument(candidate.id, label);
        selectedParentText.setText("선택한 상위 주제: " + label);
        clearParentButton.setVisibility(View.VISIBLE);
    }

    private void clearParentSelection() {
        selectedParentDocumentId = "";
        captureDependencies.settings.clearParentDocument();
        selectedParentText.setText(defaultParentMessage());
        clearParentButton.setVisibility(View.GONE);
    }

    private static String defaultParentMessage() {
        return "선택 안 함 — 직전에 Android 클립보드로 저장한 문서를 자동 연결합니다.";
    }

    private void submitClipboard(Button button, String targetFolder) {
        CharSequence text = new ClipboardReader(this).readText();
        if (text == null) {
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
            CaptureResult result = captureDependencies.captureUseCase.execute(
                    text,
                    false,
                    captureDependencies.settings.source(),
                    targetFolder,
                    selectedParentDocumentId,
                    Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID)
            );
            runOnUiThread(() -> {
                refreshAutoCaptureUi();
                finishClipboardSubmit(button, resultMessage(result.status));
            });
        });
    }

    private void enableAutoCapture() {
        if (captureDependencies.settings.serverUrl().isEmpty()) {
            rejectAutoCapture("자동 저장을 시작하려면 서버 주소를 저장하세요.");
            return;
        }
        if (captureDependencies.settings.targetFolder().isEmpty()) {
            rejectAutoCapture("먼저 개인 Vault 저장 폴더를 선택하세요.");
            return;
        }
        captureDependencies.settings.setState(AutoCaptureState.RUNNING);
        startForegroundService(new Intent(this, ClipboardCaptureService.class)
                .setAction(ClipboardCaptureService.ACTION_START));
        refreshAutoCaptureUi();
    }

    private void disableAutoCapture() {
        captureDependencies.settings.setState(AutoCaptureState.DISABLED);
        stopService(new Intent(this, ClipboardCaptureService.class));
        refreshAutoCaptureUi();
    }

    private void rejectAutoCapture(String message) {
        captureDependencies.settings.setState(AutoCaptureState.DISABLED);
        autoCaptureSwitch.setChecked(false);
        autoCaptureStatus.setText(message);
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    private void refreshRunningService() {
        if (captureDependencies.settings.state() != AutoCaptureState.DISABLED) {
            startForegroundService(new Intent(this, ClipboardCaptureService.class)
                    .setAction(ClipboardCaptureService.ACTION_START));
        }
    }

    private void refreshAutoCaptureUi() {
        if (autoCaptureStatus == null) {
            return;
        }
        AutoCaptureState state = captureDependencies.settings.state();
        autoCaptureSwitch.setChecked(state != AutoCaptureState.DISABLED);
        CaptureSource source = captureDependencies.settings.source();
        if (state == AutoCaptureState.DISABLED) {
            autoCaptureStatus.setText("자동 저장이 꺼져 있습니다.");
        } else if (state == AutoCaptureState.PAUSED) {
            autoCaptureStatus.setText("자동 저장이 일시 중지되었습니다.");
        } else if (state == AutoCaptureState.ERROR) {
            autoCaptureStatus.setText("서버에 연결할 수 없습니다. 복사한 내용은 휴대폰에 임시 보관합니다.");
        } else if (source == CaptureSource.CHATGPT) {
            autoCaptureStatus.setText("ChatGPT 클립보드 자동 저장이 실행 중입니다.");
        } else if (source == CaptureSource.CODEX) {
            autoCaptureStatus.setText("Codex 답변 클립보드 자동 저장이 실행 중입니다.");
        } else {
            autoCaptureStatus.setText("일반 텍스트 클립보드 자동 저장이 실행 중입니다.");
        }
        pendingStatus.setText("전송 대기: " + captureDependencies.localStore.pendingCount() + "건");
    }

    private void restoreParentSelection() {
        selectedParentDocumentId = captureDependencies.settings.parentDocumentId();
        String label = captureDependencies.settings.parentDocumentLabel();
        if (!selectedParentDocumentId.isEmpty() && !label.isEmpty()) {
            selectedParentText.setText("선택한 상위 주제: " + label);
            clearParentButton.setVisibility(View.VISIBLE);
        }
    }

    private static String resultMessage(CaptureStatus status) {
        switch (status) {
            case SAVED:
                return "클립보드 내용을 저장했습니다.";
            case DUPLICATE:
                return "이미 저장한 내용입니다.";
            case QUEUED:
                return "서버 연결 실패: 복사한 내용을 휴대폰에 임시 보관했습니다.";
            case BLOCKED_SENSITIVE:
                return "민감정보로 판단되어 저장하지 않았습니다.";
            case SKIPPED:
                return "클립보드에 저장할 텍스트가 없습니다.";
            default:
                return "클립보드 내용을 저장하지 못했습니다.";
        }
    }

    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1001);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (captureDependencies != null) {
            refreshAutoCaptureUi();
            if (captureDependencies.settings.state() == AutoCaptureState.RUNNING) {
                startForegroundService(new Intent(this, ClipboardCaptureService.class)
                        .setAction(ClipboardCaptureService.ACTION_CHECK));
            }
        }
    }

    private void finishClipboardSubmit(Button button, String message) {
        button.setEnabled(true);
        button.setText("클립보드 내용 저장");
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }

    @Override
    protected void onDestroy() {
        codexExecutor.shutdownNow();
        executor.shutdownNow();
        super.onDestroy();
    }
}
