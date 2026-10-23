package com.saarthi.assistant

import android.content.Context
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.core.app.NotificationManagerCompat
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class NativePersistenceTest {
    private val context = InstrumentationRegistry.getInstrumentation().targetContext
    @Test fun preferenceCiphertextSurvivesReadAndCanBeDeleted() {
        val key = "instrumented." + UUID.randomUUID()
        try {
            SecurePreferences.set(context, key, "private-fixture-value")
            val raw = context.getSharedPreferences("saarthi.preferences.v1", Context.MODE_PRIVATE).getString(key, null)
            assertNotNull(raw)
            assertFalse(raw!!.contains("private-fixture-value"))
            assertEquals("private-fixture-value", SecurePreferences.get(context, key))
            SecurePreferences.set(context, key, null)
            assertNull(SecurePreferences.get(context, key))
        } finally { SecurePreferences.set(context, key, null) }
    }
    @Test fun remindersPersistDeliverOnceAndCancel() {
        val id = UUID.randomUUID().toString()
        val task = JSONObject().put("id", id).put("text", "Instrumented reminder")
            .put("at", System.currentTimeMillis() + 3600000).put("repeat", "once")
        try {
            assertTrue(ReminderStore.schedule(context, task).getBoolean("ok"))
            assertTrue(ReminderStore.list(context).toString().contains(id))
            assertFalse(ReminderStore.deliver(context, id)) // Never deliver before due.
            val prefs = context.getSharedPreferences("saarthi.tasks.v1", Context.MODE_PRIVATE)
            val persisted = JSONObject(prefs.getString("task.$id", null)!!)
            persisted.put("at", System.currentTimeMillis() - 1000)
            assertTrue(prefs.edit().putString("task.$id", persisted.toString()).commit())
            assertTrue(ReminderStore.deliver(context, id))
            val first = prefs.getString("task.$id", null)
            assertEquals("delivered", JSONObject(first!!).getString("status"))
            assertTrue(ReminderStore.deliver(context, id))
            assertEquals(first, prefs.getString("task.$id", null)) // Duplicate worker is a no-op.
            assertTrue(ReminderStore.cancel(context, id).getBoolean("ok"))
            assertFalse(ReminderStore.list(context).toString().contains(id))
        } finally { ReminderStore.cancel(context, id) }
    }
}
