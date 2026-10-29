package com.fitmind.app.core.database

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [ChatSessionEntity::class, ConversationMessageEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class FitMindDatabase : RoomDatabase() {
    abstract fun dao(): FitMindDao
}
