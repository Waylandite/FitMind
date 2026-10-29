package com.fitmind.app.data

import com.fitmind.app.core.database.ChatSessionEntity
import com.fitmind.app.core.database.ConversationMessageEntity
import com.fitmind.app.core.database.FitMindDao
import com.fitmind.app.core.model.ChatMessage
import com.fitmind.app.core.model.ChatSession
import com.fitmind.app.core.model.Clarification
import com.fitmind.app.core.model.MessageRole
import com.fitmind.app.core.model.PendingWorkflow
import com.fitmind.app.core.network.ChatStreamClient
import com.fitmind.app.core.network.ChatStreamEvent
import com.fitmind.app.core.network.FitMindApi
import com.fitmind.app.core.network.dto.ChatRequestDto
import com.fitmind.app.core.network.dto.ClarificationInputDto
import com.fitmind.app.core.network.dto.CreateSessionRequestDto
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

data class SessionRestore(
    val clarification: Clarification?,
    val pendingWorkflow: PendingWorkflow?,
)

interface ChatRepositoryContract {
    fun observeSessions(ownerId: Long): Flow<List<ChatSession>>
    fun observeMessages(ownerId: Long, sessionId: Long): Flow<List<ChatMessage>>
    suspend fun refreshSessions(ownerId: Long): List<ChatSession>
    suspend fun createSession(ownerId: Long): ChatSession
    suspend fun restoreSession(ownerId: Long, sessionId: Long): SessionRestore
    fun streamMessage(
        threadId: String,
        message: String,
        clarification: ClarificationInputDto? = null,
    ): Flow<ChatStreamEvent>
}

@Singleton
class ChatRepository @Inject constructor(
    private val api: FitMindApi,
    private val dao: FitMindDao,
    private val streamClient: ChatStreamClient,
) : ChatRepositoryContract {
    override fun observeSessions(ownerId: Long): Flow<List<ChatSession>> =
        dao.observeSessions(ownerId).map { entities -> entities.map { it.toDomain() } }

    override fun observeMessages(ownerId: Long, sessionId: Long): Flow<List<ChatMessage>> =
        dao.observeMessages(ownerId, sessionId).map { entities -> entities.map { it.toDomain() } }

    override suspend fun refreshSessions(ownerId: Long): List<ChatSession> {
        val remote = api.sessions()
        val sessions = remote.map { it.toDomain() }
        dao.deleteSessions(ownerId)
        dao.upsertSessions(sessions.map { it.toEntity(ownerId) })
        return sessions
    }

    override suspend fun createSession(ownerId: Long): ChatSession {
        val created = api.createSession(
            CreateSessionRequestDto(
                threadId = "android-${ownerId}-${UUID.randomUUID()}",
                title = "新的会话",
            ),
        ).toDomain()
        dao.upsertSessions(listOf(created.toEntity(ownerId)))
        return created
    }

    override suspend fun restoreSession(ownerId: Long, sessionId: Long): SessionRestore = coroutineScope {
        val messagesTask = async { api.messages(sessionId) }
        val clarificationTask = async { api.clarification(sessionId)?.toDomain() }
        val workflowTask = async { api.pendingWorkflow(sessionId)?.toDomain() }

        val messages = messagesTask.await()
        dao.deleteMessages(ownerId, sessionId)
        dao.upsertMessages(
            messages.mapNotNull { message ->
                val actualSessionId = message.sessionId ?: return@mapNotNull null
                ConversationMessageEntity(
                    ownerId = ownerId,
                    id = message.id,
                    sessionId = actualSessionId,
                    role = message.role,
                    messageText = message.messageText,
                    createdAt = message.createdAt,
                )
            },
        )
        SessionRestore(clarificationTask.await(), workflowTask.await())
    }

    override fun streamMessage(
        threadId: String,
        message: String,
        clarification: ClarificationInputDto?,
    ): Flow<ChatStreamEvent> = streamClient.stream(
        ChatRequestDto(threadId = threadId, message = message, clarification = clarification),
    )

    private fun ChatSession.toEntity(ownerId: Long) = ChatSessionEntity(
        ownerId, id, threadId, title, status, startedAt, lastMessageAt,
    )

    private fun ChatSessionEntity.toDomain() = ChatSession(
        id, threadId, title, status, startedAt, lastMessageAt,
    )

    private fun ConversationMessageEntity.toDomain() = ChatMessage(
        id = "server-$id",
        serverId = id,
        sessionId = sessionId,
        role = when (role) {
            "user" -> MessageRole.USER
            "assistant" -> MessageRole.ASSISTANT
            else -> MessageRole.SYSTEM
        },
        content = messageText,
        createdAt = createdAt,
    )
}
