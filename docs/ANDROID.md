# SAARTHI Android

Capacitor 7 packages the existing frontend. Kotlin supplies constrained device operations and WorkManager persistence. Public application assets are bundled locally; backend, environment files, tests and repository metadata are excluded. No external website is given a native bridge.

## Build

Requirements: Node 22+, JDK 21, Android SDK platform 35 and build tools 35.0.0.

```bash
npm ci
npm run android:build
```

APK: `android/app/build/outputs/apk/debug/app-debug.apk`.
CI uploads the APK and JVM reports in the `saarthi-android-debug` artifact. A second job boots Android API 35 and runs three instrumentation tests: encrypted preference roundtrip/delete, reminder persistence/delivery/deduplication/cancel, and packaged assistant initialization/native network invocation. These three tests returned `OK (3 tests)` on application commit `dbde615` with the complete Android workflow VERIFIED at `b624069`; physical-device speech/camera/location/intents and natural background timing remain unverified.

Default builds deliberately contain no implicit cloud destination. They support local utilities and retained local work. To enable cloud requests against an approved deployment:

```bash
SAARTHI_ANDROID_API_URL=https://your-approved-backend.example npm run android:build
```

The value must be an HTTPS origin without credentials, query, fragment or path. It is public configuration, never an API key. Allow `https://localhost` in that backend's `SAARTHI_ALLOWED_ORIGINS`. Keep `SAARTHI_ACCESS_TOKEN` on private deployments and enter its value through Settings for the current tab. The existing public preview predates these CORS changes; this session has not deployed new code. Capacitor HTTP is not used to bypass CORS. Streaming stays on the browser fetch path.

## Supported boundary

All frontend device calls return `{ok, action, data}` or `{ok:false, action, code, message}`. Unsupported browser operations are errors, never simulated device success.

- `open whatsapp/youtube/maps/gmail/chrome/instagram`: fixed package allowlist; unavailable applications return a structured error. No arbitrary package/intent/shell execution.
- `set a timer for 5 minutes` / `set an alarm for 08:30`: open Clock's review UI. Confirm there; SAARTHI does not claim it has created the clock entry.
- Foreground location, camera capture, network status and local notifications use official Capacitor plugins. Location returns coordinates, timestamp and accuracy; denied permissions are handled.
- Document import uses Android's document picker with bounded reads. PDF text extraction still needs a backend; there is no offline OCR.
- Native HTML/JSON/ZIP export uses Android's create-document picker, writes only the selected URI, enforces a 1 MB limit and reports cancellation. Multi-file ZIP assembly currently uses the backend export API; offline multi-file ZIP export is not claimed.
- Native speech uses Android speech-recognition activity and TextToSpeech with `en-IN`, `hi-IN`, `mr-IN`. Voice availability depends on installed engines/language data. Android Back cancels the external recognizer; Stop suppresses late results and stops TTS. No background microphone service or always-listening wake word.
- Preferences boundary uses AES-GCM with an Android Keystore key. Provider/access keys remain tab-memory only; the app does not automatically persist them in native preferences. Clear site data/uninstall behavior needs physical verification.
- Android WorkManager handles one-off and daily reminder notifications with unique work names and stable notification tags. Repeated delivery checks suppress duplicates. Daily means 24 hours, not a calendar timezone/DST recurrence. Exact delivery is not guaranteed; force-stop, disabled notifications and battery policies can prevent/delay delivery. No cloud AI jobs run in the background.

## Security and data

Backups, cleartext traffic, native WebView debugging and Capacitor logging are disabled. No broad storage, call/SMS, background location, exact-alarm or background microphone permission is requested. App launching queries enumerate only the fixed allowlist. Native file operations use scoped system pickers.

AppForge preview frames have opaque sandbox origins and restrictive CSP. The activity removes the legacy JavascriptInterface fallback and requires a modern WebView message listener with main-frame checks. Unsupported WebViews show an update requirement. The emulator startup/network test must pass to validate this bridge configuration.

The browser library/history/notes remain local WebView data; reminder text is private app preference data with backup disabled. Android Keystore protection applies to the explicit secure-preference boundary, not every browser database. Do not store credentials in memory notes. Exports intentionally contain selected user data and are written only after the system picker confirms a destination.

## Physical-device acceptance matrix

| Journey | Required checks |
|---|---|
| First install | Branding, offline shell, launch, safe areas and system back |
| Cloud chat | Approved backend/CORS, access gate, BYOK response, streaming, history and model switch |
| Speech | English/Hindi/Marathi transcription and playback, language unavailable, permission denial, interruption, recognizer cancellation, Bluetooth |
| App intents | Installed and missing WhatsApp/YouTube/Maps, Clock timer/alarm review |
| Permissions | Approximate location, precise denied, disabled location services, camera cancellation |
| Notification | Granted/denied/disabled channel; reminder fires once and tapping opens SAARTHI |
| Background | Process death, reboot, doze, battery saver and force-stop; record delayed/missed reminders accurately |
| Files | Import TXT/PDF, over-limit rejection, export HTML/JSON/ZIP to Files, cancellation and actual byte contents |
| UI | Keyboard open, rotation, 360px width, TalkBack, large font and reduced motion |
| Privacy | Forget keys, revoke memory consent, delete notes/documents/history, uninstall/reinstall |

Physical-device scenarios remain IMPLEMENTED BUT UNVERIFIED until executed. An APK build is not hardware verification.
