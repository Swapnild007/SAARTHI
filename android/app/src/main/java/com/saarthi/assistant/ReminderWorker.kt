package com.saarthi.assistant

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.*
import com.getcapacitor.JSObject
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID
import java.util.concurrent.TimeUnit

object ReminderStore {
    private fun prefs(c: Context) = c.getSharedPreferences("saarthi.tasks.v1", Context.MODE_PRIVATE)
    @Synchronized fun list(c: Context): JSONArray = JSONArray().apply {
        prefs(c).all.filterKeys { it.startsWith("task.") }.values.forEach { put(JSONObject(it as String)) }
    }
    @Synchronized fun schedule(c: Context, input: JSONObject): JSObject {
        val id = input.optString("id")
        require(runCatching { UUID.fromString(id) }.isSuccess)
        val at = input.optLong("at")
        val text = input.optString("text").trim()
        val repeat = input.optString("repeat", "once")
        require(ReminderRules.valid(at, System.currentTimeMillis(), text, repeat))
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(c, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
            return JSObject().put("ok", false).put("code", "PERMISSION_DENIED").put("message", "Enable notification permission before scheduling.")
        require(list(c).length() < 200 || prefs(c).contains("task.$id"))
        val task = JSONObject().put("id", id).put("at", at).put("text", text).put("repeat", repeat).put("status", "scheduled")
        check(prefs(c).edit().putString("task.$id", task.toString()).commit())
        val data = Data.Builder().putString("id", id).build()
        val delay = at - System.currentTimeMillis()
        if (repeat == "daily") {
            val request = PeriodicWorkRequestBuilder<ReminderWorker>(24, TimeUnit.HOURS)
                .setInputData(data).setInitialDelay(delay.coerceAtLeast(0), TimeUnit.MILLISECONDS).build()
            WorkManager.getInstance(c).enqueueUniquePeriodicWork("saarthi.$id", ExistingPeriodicWorkPolicy.UPDATE, request).result.get()
        } else {
            val request = OneTimeWorkRequestBuilder<ReminderWorker>().setInputData(data)
                .setInitialDelay(delay.coerceAtLeast(0), TimeUnit.MILLISECONDS).build()
            WorkManager.getInstance(c).enqueueUniqueWork("saarthi.$id", ExistingWorkPolicy.REPLACE, request).result.get()
        }
        return JSObject().put("ok", true).put("task", task).put("message", "Reminder scheduled. Android may delay delivery; exact time is not guaranteed.")
    }
    @Synchronized fun cancel(c: Context, id: String): JSObject {
        require(runCatching { UUID.fromString(id) }.isSuccess)
        // Remove state first: a racing worker checks it under this same lock.
        check(prefs(c).edit().remove("task.$id").commit())
        WorkManager.getInstance(c).cancelUniqueWork("saarthi.$id")
        NotificationManagerCompat.from(c).cancel(id, 1)
        return JSObject().put("ok", true).put("message", "Reminder cancelled.")
    }
    @Synchronized fun deliver(c: Context, id: String): Boolean {
        val raw = prefs(c).getString("task.$id", null) ?: return true
        val task = JSONObject(raw)
        if (task.optString("status") == "delivered") return true
        val now = System.currentTimeMillis()
        val scheduled = task.getLong("at")
        if (now < scheduled) return false
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(c, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            task.put("status", "permission_denied")
            prefs(c).edit().putString("task.$id", task.toString()).commit()
            return true
        }
        val manager = c.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(NotificationChannel("saarthi-reminders", "SAARTHI reminders", NotificationManager.IMPORTANCE_DEFAULT))
        val intent = PendingIntent.getActivity(c, 0, Intent(c, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val notification = NotificationCompat.Builder(c, "saarthi-reminders").setSmallIcon(com.saarthi.assistant.R.drawable.ic_stat_saarthi)
            .setContentTitle("SAARTHI reminder").setContentText(task.getString("text")).setContentIntent(intent).setAutoCancel(true).build()
        // Stable tag/id replaces a notification if a process dies between notify and commit.
        manager.notify(id, 1, notification)
        task.put("lastDeliveredAt", now)
        if (task.optString("repeat") == "daily") {
            task.put("at", ReminderRules.nextDaily(scheduled, now)).put("status", "scheduled")
        } else task.put("status", "delivered")
        return prefs(c).edit().putString("task.$id", task.toString()).commit()
    }
}

class ReminderWorker(context: Context, params: WorkerParameters) : Worker(context, params) {
    override fun doWork(): Result = try {
        val id = inputData.getString("id") ?: return Result.failure()
        if (ReminderStore.deliver(applicationContext, id)) Result.success() else Result.retry()
    } catch (_: Exception) { if (runAttemptCount < 3) Result.retry() else Result.failure() }
}
