package dev.mde.autoknowledge;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.net.ConnectivityManager;
import android.net.Network;
import android.os.IBinder;
import android.provider.Settings;
import android.util.Log;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class ClipboardCaptureService extends Service {
    static final String ACTION_START = "dev.mde.autoknowledge.capture.START";
    static final String ACTION_CHECK = "dev.mde.autoknowledge.capture.CHECK";
    static final String ACTION_PAUSE = "dev.mde.autoknowledge.capture.PAUSE";
    static final String ACTION_RESUME = "dev.mde.autoknowledge.capture.RESUME";
    static final String ACTION_DISABLE = "dev.mde.autoknowledge.capture.DISABLE";
    static final String ACTION_RETRY = "dev.mde.autoknowledge.capture.RETRY";
    private static final String CHANNEL_SERVICE = "auto_capture_service";
    private static final String CHANNEL_RESULTS = "auto_capture_results";
    private static final int SERVICE_NOTIFICATION_ID = 4100;
    private static final int RESULT_NOTIFICATION_ID = 4101;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private CaptureDependencies dependencies;
    private ClipboardReader clipboardReader;
    private boolean listening;
    private ConnectivityManager connectivityManager;
    private ConnectivityManager.NetworkCallback networkCallback;
    private final android.content.ClipboardManager.OnPrimaryClipChangedListener listener =
            this::captureCurrentClipboard;

    @Override
    public void onCreate() {
        super.onCreate();
        dependencies = new CaptureDependencies(this);
        clipboardReader = new ClipboardReader(this);
        createNotificationChannels();
        registerNetworkCallback();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? ACTION_START : intent.getAction();
        if (ACTION_DISABLE.equals(action)) {
            dependencies.settings.setState(AutoCaptureState.DISABLED);
            stopSelf();
            return START_NOT_STICKY;
        }
        if (ACTION_PAUSE.equals(action)) {
            dependencies.settings.setState(AutoCaptureState.PAUSED);
            unregisterClipboardListener();
        } else if (ACTION_RESUME.equals(action)) {
            dependencies.settings.setState(AutoCaptureState.RUNNING);
            registerClipboardListener();
        } else if (ACTION_RETRY.equals(action)) {
            executor.execute(() -> dependencies.retryUseCase.execute(true));
        } else if (ACTION_CHECK.equals(action)) {
            captureCurrentClipboard();
        } else if (dependencies.settings.state() == AutoCaptureState.RUNNING) {
            registerClipboardListener();
            executor.execute(() -> dependencies.retryUseCase.execute(false));
        }

        AutoCaptureState state = dependencies.settings.state();
        if (state == AutoCaptureState.DISABLED) {
            stopSelf();
            return START_NOT_STICKY;
        }
        startForeground(SERVICE_NOTIFICATION_ID, serviceNotification(state));
        return START_NOT_STICKY;
    }

    private void captureCurrentClipboard() {
        if (dependencies.settings.state() != AutoCaptureState.RUNNING) {
            return;
        }
        CharSequence text = clipboardReader.readText();
        if (text == null) {
            return;
        }
        executor.execute(() -> {
            CaptureSource source = dependencies.settings.source();
            CaptureResult result = dependencies.captureUseCase.execute(
                    text,
                    true,
                    source,
                    dependencies.settings.targetFolder(),
                    dependencies.settings.parentDocumentId(),
                    Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID)
            );
            String shortHash = result.contentHash.length() >= 8
                    ? result.contentHash.substring(0, 8)
                    : "none";
            Log.i(
                    "AutoKnowledgeCapture",
                    "Capture result: source=" + source.name()
                            + " status=" + result.status.name()
                            + " hash=" + shortHash
            );
            notifyResult(source, result.status);
        });
    }

    private void registerClipboardListener() {
        if (!listening) {
            clipboardReader.manager().addPrimaryClipChangedListener(listener);
            listening = true;
        }
    }

    private void unregisterClipboardListener() {
        if (listening) {
            clipboardReader.manager().removePrimaryClipChangedListener(listener);
            listening = false;
        }
    }

    private Notification serviceNotification(AutoCaptureState state) {
        CaptureSource source = dependencies.settings.source();
        String body;
        if (state == AutoCaptureState.PAUSED) {
            body = "자동 저장이 일시 중지되었습니다.";
        } else if (source == CaptureSource.CHATGPT) {
            body = "ChatGPT에서 복사한 답변을 감지합니다.";
        } else if (source == CaptureSource.CODEX) {
            body = "Codex Remote에서 복사한 답변을 감지합니다.";
        } else {
            body = "복사한 일반 텍스트를 감지합니다.";
        }
        Notification.Builder builder = new Notification.Builder(this, CHANNEL_SERVICE)
                .setSmallIcon(android.R.drawable.ic_menu_save)
                .setContentTitle("AutoKnowledge-Lite 자동 저장 실행 중")
                .setContentText(body)
                .setOngoing(true)
                .setContentIntent(activityIntent());
        if (state == AutoCaptureState.PAUSED) {
            builder.addAction(action("다시 시작", ACTION_RESUME, 2));
            builder.addAction(action("자동 저장 끄기", ACTION_DISABLE, 3));
        } else {
            builder.addAction(action("일시 중지", ACTION_PAUSE, 1));
        }
        return builder.build();
    }

    private Notification.Action action(String title, String action, int requestCode) {
        Intent intent = new Intent(this, ClipboardCaptureService.class).setAction(action);
        PendingIntent pendingIntent = PendingIntent.getService(
                this,
                requestCode,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        return new Notification.Action.Builder(
                android.R.drawable.ic_media_play,
                title,
                pendingIntent
        ).build();
    }

    private PendingIntent activityIntent() {
        return PendingIntent.getActivity(
                this,
                0,
                new Intent(this, MainActivity.class),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
    }

    private void notifyResult(CaptureSource source, CaptureStatus status) {
        if (status == CaptureStatus.SKIPPED) {
            return;
        }
        String title;
        String body = "";
        switch (status) {
            case SAVED:
                title = source.titlePrefix + "을 저장했습니다.";
                break;
            case DUPLICATE:
                title = "이미 저장한 내용입니다.";
                break;
            case QUEUED:
                title = "서버 연결 실패";
                body = "복사한 내용을 휴대폰에 임시 보관했습니다.";
                break;
            case BLOCKED_SENSITIVE:
                title = "민감정보로 판단되어 자동 저장하지 않았습니다.";
                break;
            default:
                title = "클립보드 내용을 저장하지 못했습니다.";
                body = "AutoKnowledge-Lite 앱에서 상태를 확인하세요.";
                break;
        }
        Notification notification = new Notification.Builder(this, CHANNEL_RESULTS)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(title)
                .setContentText(body)
                .setAutoCancel(true)
                .setContentIntent(activityIntent())
                .build();
        getSystemService(NotificationManager.class).notify(RESULT_NOTIFICATION_ID, notification);
    }

    private void createNotificationChannels() {
        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel(
                CHANNEL_SERVICE,
                "클립보드 자동 저장",
                NotificationManager.IMPORTANCE_LOW
        ));
        manager.createNotificationChannel(new NotificationChannel(
                CHANNEL_RESULTS,
                "저장 결과",
                NotificationManager.IMPORTANCE_DEFAULT
        ));
    }

    private void registerNetworkCallback() {
        connectivityManager = getSystemService(ConnectivityManager.class);
        networkCallback = new ConnectivityManager.NetworkCallback() {
            @Override
            public void onAvailable(Network network) {
                executor.execute(() -> dependencies.retryUseCase.execute(false));
            }
        };
        try {
            connectivityManager.registerDefaultNetworkCallback(networkCallback);
        } catch (RuntimeException ignored) {
            networkCallback = null;
        }
    }

    @Override
    public void onDestroy() {
        unregisterClipboardListener();
        if (networkCallback != null) {
            try {
                connectivityManager.unregisterNetworkCallback(networkCallback);
            } catch (RuntimeException ignored) {
                // Already unregistered by the system.
            }
        }
        executor.shutdownNow();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
