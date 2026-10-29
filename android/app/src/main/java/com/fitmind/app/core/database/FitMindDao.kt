package com.fitmind.app.core.database

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
interface FitMindDao {
    @Query(
        "SELECT * FROM chat_sessions WHERE ownerId = :ownerId " +
            "ORDER BY COALESCE(lastMessageAt, startedAt) DESC",
    )
    fun observeSessions(ownerId: Long): Flow<List<ChatSessionEntity>>

    @Upsert
    suspend fun upsertSessions(sessions: List<ChatSessionEntity>)

    @Query("DELETE FROM chat_sessions WHERE ownerId = :ownerId")
    suspend fun deleteSessions(ownerId: Long)

    @Query(
        "SELECT * FROM conversation_messages WHERE ownerId = :ownerId AND sessionId = :sessionId " +
            "ORDER BY createdAt ASC, id ASC",
    )
    fun observeMessages(ownerId: Long, sessionId: Long): Flow<List<ConversationMessageEntity>>

    @Upsert
    suspend fun upsertMessages(messages: List<ConversationMessageEntity>)

    @Query("DELETE FROM conversation_messages WHERE ownerId = :ownerId AND sessionId = :sessionId")
    suspend fun deleteMessages(ownerId: Long, sessionId: Long)

    @Query("DELETE FROM conversation_messages WHERE ownerId = :ownerId")
    suspend fun deleteAllMessages(ownerId: Long)

    @Query("DELETE FROM chat_sessions")
    suspend fun deleteEverySession()

    @Query("DELETE FROM conversation_messages")
    suspend fun deleteEveryMessage()
}
