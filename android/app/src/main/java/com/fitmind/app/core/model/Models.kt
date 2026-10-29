package com.fitmind.app.core.model

import kotlinx.serialization.json.JsonObject

data class User(
    val id: Long,
    val email: String,
    val username: String,
    val displayName: String?,
    val avatarUrl: String?,
)

data class ChatSession(
    val id: Long,
    val threadId: String,
    val title: String?,
    val status: String,
    val startedAt: String,
    val lastMessageAt: String?,
)

data class ChatMessage(
    val id: String,
    val serverId: Long? = null,
    val sessionId: Long,
    val role: MessageRole,
    val content: String,
    val createdAt: String,
    val isStreaming: Boolean = false,
    val trace: List<AgentTraceStep> = emptyList(),
    val draft: PendingWorkflow? = null,
    val clarification: Clarification? = null,
)

enum class MessageRole { USER, ASSISTANT, SYSTEM }

data class AgentTraceStep(
    val workflow: String,
    val status: String,
    val node: String,
    val title: String,
    val detail: String,
)

data class DraftActions(
    val label: String,
    val hint: String,
    val confirmText: String,
    val cancelText: String,
    val correctionText: String,
    val correctionPrefill: String,
)

data class PendingWorkflow(
    val workflow: String,
    val intent: String,
    val draftId: Long,
    val draft: JsonObject,
    val actions: DraftActions,
    val updatedAt: String,
)

data class ClarificationOption(
    val intent: String,
    val label: String,
    val description: String,
)

data class Clarification(
    val id: Long,
    val action: String,
    val question: String,
    val options: List<ClarificationOption>,
    val attempt: Int,
    val maxAttempts: Int,
    val status: String,
)
