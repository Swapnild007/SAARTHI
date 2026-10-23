package com.saarthi.assistant

import org.junit.Assert.*
import org.junit.Test

class ReminderRulesTest {
    @Test fun rejectsInvalidAndPastRequests() {
        assertFalse(ReminderRules.valid(999, 1000, "Reminder", "once"))
        assertFalse(ReminderRules.valid(1001, 1000, " ", "once"))
        assertFalse(ReminderRules.valid(1001, 1000, "x".repeat(501), "once"))
        assertFalse(ReminderRules.valid(1001, 1000, "Reminder", "hourly"))
        assertFalse(ReminderRules.valid(1000 + 367 * ReminderRules.DAY, 1000, "Reminder", "once"))
    }
    @Test fun permitsSupportedFutureRequests() {
        assertTrue(ReminderRules.valid(1001, 1000, "Review briefing", "daily"))
        assertTrue(ReminderRules.valid(1001, 1000, "Take a break", "once"))
    }
    @Test fun dailyRecoveryDeliversOnlyOneCatchUpOccurrence() {
        val scheduled = 1000L
        val now = scheduled + 5 * ReminderRules.DAY + 30000
        val next = ReminderRules.nextDaily(scheduled, now)
        assertEquals(scheduled + 6 * ReminderRules.DAY, next)
        assertTrue(next > now)
        assertEquals(scheduled + ReminderRules.DAY, ReminderRules.nextDaily(scheduled, scheduled))
    }
}
