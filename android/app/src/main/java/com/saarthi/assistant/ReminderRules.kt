package com.saarthi.assistant

object ReminderRules {
    const val DAY = 86400000L
    fun valid(at: Long, now: Long, text: String, repeat: String): Boolean =
        text.isNotBlank() && text.length <= 500 && at > now && at - now <= 366L * DAY && repeat in setOf("once", "daily")
    fun nextDaily(scheduled: Long, now: Long): Long {
        require(scheduled > 0 && now >= scheduled)
        return scheduled + ((now - scheduled) / DAY + 1) * DAY
    }
}
