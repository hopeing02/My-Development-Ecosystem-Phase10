# MDE Knowledge Viewer Android

PC에서 실행 중인 MDE Knowledge Viewer를 Android WebView로 표시하는 읽기 전용 앱입니다.
앱은 서버 주소만 저장하며 WebView 캐시를 사용하지 않고 다른 Origin 이동을 차단합니다.

## PC 서버

PC의 비공개 LAN IP 또는 Tailscale IP 하나에만 서버를 바인딩합니다.

```powershell
uv run mde knowledge serve --host 192.168.0.10 --no-open
```

Android 앱에 `http://192.168.0.10:8765`를 저장합니다. 공용 네트워크나 포트
포워딩으로 서버를 노출하지 마세요.

## 빌드

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
Set-Location apps/knowledge-viewer/android
.\gradlew.bat testDebugUnitTest assembleDebug --no-daemon --console=plain
```

APK는 `app/build/outputs/apk/debug/app-debug.apk`에 생성됩니다.

빌드 후 휴대폰 브라우저에서 다음 고정 주소로 직접 다운로드할 수 있습니다.

```text
http://PC-IP:8765/downloads/mde-knowledge-viewer.apk
```
