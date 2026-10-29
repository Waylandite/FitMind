package com.fitmind.app.core.network

import com.fitmind.app.core.network.dto.ClarificationDto
import com.fitmind.app.core.network.dto.DraftActionsDto
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

sealed interface ChatStreamEvent {
    data class IntentRecognized(
        val intent: String,
        val confidence: Double,
        val source: String,
        val reason: String,
    ) : ChatStreamEvent

    data class SessionConnected(val threadId: String, val sessionId: Long) : ChatStreamEvent

    data class AgentState(
        val workflow: String,
        val status: String,
        val node: String,
        val title: String,
        val detail: String,
    ) : ChatStreamEvent

    data class Workflow(
        val workflow: String,
        val action: String,
        val draftId: Long?,
        val draft: JsonObject?,
        val draftActions: DraftActionsDto?,
    ) : ChatStreamEvent

    data class Clarification(val value: ClarificationDto) : ChatStreamEvent
    data class Delta(val content: String) : ChatStreamEvent
    data class Done(val reply: String, val sessionId: Long?, val intent: String?, val workflow: String?) : ChatStreamEvent
    data class Error(val message: String) : ChatStreamEvent
    data class Unknown(val type: String) : ChatStreamEvent
}

@Serializable
internal data class StreamEnvelope(
    val type: String,
    val intent: String? = null,
    val confidence: Double? = null,
    val source: String? = null,
    val reason: String? = null,
    @SerialName("thread_id") val threadId: String? = null,
    @SerialName("session_id") val sessionId: Long? = null,
    val workflow: JsonElement? = null,
    val status: String? = null,
    val node: String? = null,
    val title: String? = null,
    val detail: String? = null,
    val action: String? = null,
    @SerialName("draft_id") val draftId: Long? = null,
    val draft: JsonObject? = null,
    val payload: JsonObject? = null,
    @SerialName("draft_actions") val draftActions: DraftActionsDto? = null,
    val content: String? = null,
    val reply: String? = null,
    val message: String? = null,
)
