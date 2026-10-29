package com.fitmind.app.core.database

import androidx.room.Entity
import androidx.room.Index

@Entity(
    tableName = "chat_sessions",
    primaryKeys = ["ownerId", "id"],
    indices = [Index(value = ["ownerId", "lastMessageAt"])],
)
data class ChatSessionEntity(
    val ownerId: Long,
    val id: Long,
    val threadId: String,
    val title: String?,
    val status: String,
    val startedAt: String,
    val lastMessageAt: String?,
)

@Entity(
    tableName = "conversation_messages",
    primaryKeys = ["ownerId", "id"],
    indices = [Index(value = ["ownerId", "sessionId", "createdAt"])],
)
data class ConversationMessageEntity(
    val ownerId: Long,
    val id: Long,
    val sessionId: Long,
    val role: String,
    val messageText: String,
    val createdAt: String,
)
