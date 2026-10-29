package com.fitmind.app.core.network.dto

import com.fitmind.app.core.model.ChatSession
import com.fitmind.app.core.model.Clarification
import com.fitmind.app.core.model.ClarificationOption
import com.fitmind.app.core.model.DraftActions
import com.fitmind.app.core.model.PendingWorkflow
import com.fitmind.app.core.model.User
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

@Serializable
data class UserDto(
    val id: Long,
    val email: String,
    val username: String,
    @SerialName("display_name") val displayName: String? = null,
    @SerialName("avatar_url") val avatarUrl: String? = null,
    val status: String = "active",
    @SerialName("last_login_at") val lastLoginAt: String? = null,
) {
    fun toDomain() = User(id, email, username, displayName, avatarUrl)
}

@Serializable
data class AuthTokenResponseDto(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    @SerialName("expires_in") val expiresIn: Long,
    val user: UserDto,
)

@Serializable
data class LoginRequestDto(val identifier: String, val password: String)

@Serializable
data class RegisterRequestDto(
    val email: String,
    val username: String,
    val password: String,
    @SerialName("display_name") val displayName: String? = null,
)

@Serializable
data class ChatSessionDto(
    val id: Long,
    @SerialName("user_id") val userId: Long,
    @SerialName("thread_id") val threadId: String,
    @SerialName("session_no") val sessionNo: Int,
    val title: String? = null,
    val status: String,
    @SerialName("started_at") val startedAt: String,
    @SerialName("ended_at") val endedAt: String? = null,
    @SerialName("last_message_at") val lastMessageAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
) {
    fun toDomain() = ChatSession(id, threadId, title, status, startedAt, lastMessageAt)
}

@Serializable
data class CreateSessionRequestDto(
    @SerialName("thread_id") val threadId: String,
    @SerialName("session_no") val sessionNo: Int = 1,
    val title: String? = null,
)

@Serializable
data class ConversationLogDto(
    val id: Long,
    @SerialName("user_id") val userId: Long,
    @SerialName("thread_id") val threadId: String,
    @SerialName("session_id") val sessionId: Long? = null,
    @SerialName("record_date") val recordDate: String? = null,
    val role: String,
    @SerialName("message_text") val messageText: String,
    @SerialName("intent_type") val intentType: String? = null,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class DraftActionsDto(
    val label: String,
    val hint: String,
    @SerialName("confirm_text") val confirmText: String,
    @SerialName("cancel_text") val cancelText: String,
    @SerialName("correction_text") val correctionText: String,
    @SerialName("correction_prefill") val correctionPrefill: String,
) {
    fun toDomain() = DraftActions(
        label, hint, confirmText, cancelText, correctionText, correctionPrefill,
    )
}

@Serializable
data class PendingWorkflowDto(
    val workflow: String,
    val intent: String,
    @SerialName("draft_id") val draftId: Long,
    val draft: JsonObject,
    @SerialName("draft_actions") val draftActions: DraftActionsDto,
    @SerialName("updated_at") val updatedAt: String,
) {
    fun toDomain() = PendingWorkflow(
        workflow, intent, draftId, draft, draftActions.toDomain(), updatedAt,
    )
}

@Serializable
data class ClarificationOptionDto(
    val intent: String,
    val label: String,
    val description: String,
) {
    fun toDomain() = ClarificationOption(intent, label, description)
}

@Serializable
data class ClarificationDto(
    val type: String = "clarification",
    val workflow: String = "intent_clarification",
    val action: String = "requested",
    @SerialName("clarification_id") val clarificationId: Long,
    val question: String,
    val options: List<ClarificationOptionDto> = emptyList(),
    val attempt: Int = 1,
    @SerialName("max_attempts") val maxAttempts: Int = 2,
    val status: String = "pending",
) {
    fun toDomain() = Clarification(
        clarificationId, action, question, options.map { it.toDomain() }, attempt, maxAttempts, status,
    )
}

@Serializable
data class ClarificationInputDto(
    val id: Long,
    val action: String,
    @SerialName("selected_intent") val selectedIntent: String? = null,
)

@Serializable
data class ChatRequestDto(
    @SerialName("thread_id") val threadId: String,
    val message: String,
    val clarification: ClarificationInputDto? = null,
)
