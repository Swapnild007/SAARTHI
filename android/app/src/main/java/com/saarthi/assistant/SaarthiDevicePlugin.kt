package com.saarthi.assistant

import android.app.Activity
import android.content.Intent
import android.provider.AlarmClock
import android.provider.Settings
import android.provider.OpenableColumns
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import android.util.Base64
import androidx.activity.result.ActivityResult
import com.getcapacitor.*
import com.getcapacitor.annotation.ActivityCallback
import com.getcapacitor.annotation.CapacitorPlugin
import org.json.JSONArray
import java.util.Locale
import java.util.concurrent.Executors
import java.io.ByteArrayOutputStream

/** Only explicit allowlisted operations. No arbitrary package, URI, shell or intent bridge. */
@CapacitorPlugin(name = "SaarthiDevice")
class SaarthiDevicePlugin : Plugin() {
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private val operations = Executors.newSingleThreadExecutor()
    override fun load() {
        activity.runOnUiThread { tts = TextToSpeech(context) { ttsReady = it == TextToSpeech.SUCCESS } }
    }
    private fun result(call: PluginCall, ok: Boolean, code: String, message: String) {
        call.resolve(JSObject().put("ok", ok).put("code", code).put("message", message))
    }
    @PluginMethod
    fun execute(call: PluginCall) {
        if (call.getString("action") in setOf("schedule", "tasks", "cancelTask", "secureGet", "secureSet")) {
            operations.execute {
                try {
                    when (call.getString("action")) {
                        "schedule" -> call.resolve(ReminderStore.schedule(context, call.data))
                        "tasks" -> call.resolve(JSObject().put("tasks", ReminderStore.list(context)))
                        "cancelTask" -> call.resolve(ReminderStore.cancel(context, call.getString("id") ?: ""))
                        "secureGet" -> call.resolve(JSObject().put("value", SecurePreferences.get(context, call.getString("key") ?: "")))
                        "secureSet" -> { SecurePreferences.set(context, call.getString("key") ?: "", call.getString("value")); result(call, true, "SAVED", "Encrypted preference updated.") }
                    }
                } catch (_: Exception) { result(call, false, "FAILED", "Persistent device operation failed safely.") }
            }
            return
        }
        activity.runOnUiThread {
            try {
                when (call.getString("action")) {
                    "launch" -> {
                        val packages = mapOf("whatsapp" to "com.whatsapp", "youtube" to "com.google.android.youtube",
                            "maps" to "com.google.android.apps.maps", "gmail" to "com.google.android.gm",
                            "chrome" to "com.android.chrome", "instagram" to "com.instagram.android")
                        val target = packages[call.getString("app")] ?: return@runOnUiThread result(call, false, "UNSUPPORTED", "Application is not supported.")
                        val intent = context.packageManager.getLaunchIntentForPackage(target)
                            ?: return@runOnUiThread result(call, false, "UNAVAILABLE", "Application is not installed or not launchable.")
                        activity.startActivity(intent)
                        result(call, true, "OPENED", "Application launch requested.")
                    }
                    "timer" -> {
                        val seconds = call.getInt("seconds", 0) ?: 0
                        if (seconds !in 1..86400) return@runOnUiThread result(call, false, "INVALID_INPUT", "Timer must be between one second and one day.")
                        activity.startActivity(Intent(AlarmClock.ACTION_SET_TIMER).putExtra(AlarmClock.EXTRA_LENGTH, seconds)
                            .putExtra(AlarmClock.EXTRA_MESSAGE, "SAARTHI timer").putExtra(AlarmClock.EXTRA_SKIP_UI, false))
                        result(call, true, "REVIEW_REQUIRED", "Timer opened in your Clock app. Confirm it there.")
                    }
                    "alarm" -> {
                        val hour = call.getInt("hour", -1) ?: -1
                        val minute = call.getInt("minute", -1) ?: -1
                        if (hour !in 0..23 || minute !in 0..59) return@runOnUiThread result(call, false, "INVALID_INPUT", "Use a valid hour and minute.")
                        activity.startActivity(Intent(AlarmClock.ACTION_SET_ALARM).putExtra(AlarmClock.EXTRA_HOUR, hour)
                            .putExtra(AlarmClock.EXTRA_MINUTES, minute).putExtra(AlarmClock.EXTRA_MESSAGE, "SAARTHI alarm")
                            .putExtra(AlarmClock.EXTRA_SKIP_UI, false))
                        result(call, true, "REVIEW_REQUIRED", "Alarm opened in your Clock app. Confirm it there.")
                    }
                    "settings" -> {
                        activity.startActivity(Intent(Settings.ACTION_SETTINGS))
                        result(call, true, "OPENED", "Android Settings opened.")
                    }
                    "document" -> startActivityForResult(call, Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = "*/*"
                        putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("text/plain", "text/markdown", "text/csv", "application/json", "application/pdf"))
                    }, "documentResult")
                    "listen" -> {
                        val language = language(call)
                        startActivityForResult(call, Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                            putExtra(RecognizerIntent.EXTRA_LANGUAGE, language)
                            putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak to SAARTHI")
                            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                        }, "speechResult")
                    }
                    "speak" -> {
                        if (!ttsReady) return@runOnUiThread result(call, false, "UNAVAILABLE", "Android speech engine is not ready.")
                        val supported = tts?.setLanguage(Locale.forLanguageTag(language(call))) ?: -1
                        if (supported < 0) return@runOnUiThread result(call, false, "UNSUPPORTED_LANGUAGE", "Install the requested speech language in Android Settings.")
                        tts?.stop()
                        val status = tts?.speak((call.getString("text") ?: "").take(3500), TextToSpeech.QUEUE_FLUSH, null, "saarthi")
                        result(call, status == TextToSpeech.SUCCESS, "SUBMITTED", "Speech submitted to the Android engine.")
                    }
                    "stopSpeech" -> { tts?.stop(); result(call, true, "STOPPED", "Speech stopped.") }
                    else -> result(call, false, "UNSUPPORTED", "Unsupported device operation.")
                }
            } catch (_: android.content.ActivityNotFoundException) {
                result(call, false, "UNAVAILABLE", "No installed application can handle this operation.")
            } catch (_: SecurityException) {
                result(call, false, "PERMISSION_DENIED", "Android denied this operation.")
            } catch (_: Exception) {
                result(call, false, "FAILED", "Device action failed safely.")
            }
        }
    }
    private fun language(call: PluginCall): String = call.getString("language").takeIf { it in setOf("en-IN", "hi-IN", "mr-IN") } ?: "en-IN"
    @ActivityCallback
    private fun speechResult(call: PluginCall?, response: ActivityResult) {
        if (call == null) return
        val text = response.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
        if (response.resultCode != Activity.RESULT_OK || text.isNullOrBlank()) result(call, false, "CANCELLED", "Speech input cancelled or unavailable.")
        else call.resolve(JSObject().put("transcript", text).put("ok", true))
    }
    @ActivityCallback
    private fun documentResult(call: PluginCall?, response: ActivityResult) {
        if (call == null) return
        val uri = response.data?.data
        if (response.resultCode != Activity.RESULT_OK || uri == null) { result(call, false, "CANCELLED", "Document selection cancelled."); return }
        try {
            val bytes = context.contentResolver.openInputStream(uri)?.use { input ->
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                while (output.size() <= 500000) {
                    val count = input.read(buffer, 0, minOf(buffer.size, 500001 - output.size()))
                    if (count < 0) break
                    output.write(buffer, 0, count)
                }
                output.toByteArray()
            }
            if (bytes == null || bytes.size > 500000) { result(call, false, "TOO_LARGE", "Choose a document under 500 KB."); return }
            var title = "document.txt"
            context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
                if (it.moveToFirst()) title = it.getString(0).take(180)
            }
            call.resolve(JSObject().put("ok", true).put("name", title).put("type", context.contentResolver.getType(uri))
                .put("data", Base64.encodeToString(bytes, Base64.NO_WRAP)))
        } catch (_: Exception) { result(call, false, "FAILED", "Could not read the selected document.") }
    }
    override fun handleOnPause() { tts?.stop() }
    override fun handleOnDestroy() { tts?.stop(); tts?.shutdown(); tts = null; operations.shutdown() }
}
