package com.fitmind.app.feature.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fitmind.app.core.model.AgentTraceStep
import com.fitmind.app.core.model.ChatMessage
import com.fitmind.app.core.model.ChatSession
import com.fitmind.app.core.model.Clarification
import com.fitmind.app.core.model.MessageRole
import com.fitmind.app.core.model.PendingWorkflow
import com.fitmind.app.core.network.AuthSessionStore
import com.fitmind.app.core.network.ChatStreamEvent
import com.fitmind.app.core.network.NetworkStatusProvider
import com.fitmind.app.core.network.dto.ClarificationInputDto
import com.fitmind.app.data.ChatRepositoryContract
import dagger.hilt.android.lifecycle.HiltViewModel
import java.time.Instant
import java.util.UUID
import javax.inject.Inject
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ChatUiState(
    val sessions: List<ChatSession> = emptyList(),
    val activeSession: ChatSession? = null,
    val messages: List<ChatMessage> = emptyList(),
    val composer: String = "",
    val correctionPrefill: String? = null,
    val restoredWorkflow: PendingWorkflow? = null,
    val restoredClarification: Clarification? = null,
    val isLoadingSessions: Boolean = true,
    val isLoadingMessages: Boolean = false,
    val isSending: Boolean = false,
    val isOnline: Boolean = true,
    val connectionLabel: String = "准备就绪",
    val requestStartedAt: Long? = null,
    val firstTokenAt: Long? = null,
    val error: String? = null,
    val scrollRequest: Long = 0,
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val repository: ChatRepositoryContract,
    private val authStore: AuthSessionStore,
    networkMonitor: NetworkStatusProvider,
) : ViewModel() {
    private val mutableState = MutableStateFlow(ChatUiState())
    val state: StateFlow<ChatUiState> = mutableState.asStateFlow()
    private var messagesJob: Job? = null
    private var streamJob: Job? = null
    private val ownerId: Long get() = requireNotNull(authStore.session.value).user.id

    init {
        viewModelScope.launch {
            networkMonitor.isOnline.collect { online ->
                mutableState.update { it.copy(isOnline = online) }
            }
        }
        loadSessions()
    }

    fun setComposer(value: String) = mutableState.update {
        it.copy(composer = value, correctionPrefill = null, error = null)
    }

    fun clearError() = mutableState.update { it.copy(error = null) }

    fun loadSessions() {
        viewModelScope.launch {
            repository.observeSessions(ownerId).collect { sessions ->
                mutableState.update { it.copy(sessions = sessions) }
            }
        }
        viewModelScope.launch {
            mutableState.update { it.copy(isLoadingSessions = true) }
            runCatching { repository.refreshSessions(ownerId) }
                .onSuccess { sessions ->
                    val selected = sessions.firstOrNull() ?: repository.createSession(ownerId)
                    mutableState.update { it.copy(isLoadingSessions = false) }
                    selectSession(selected)
                }
                .onFailure { error ->
                    mutableState.update {
                        it.copy(
                            isLoadingSessions = false,
                            error = if (it.sessions.isEmpty()) "无法加载会话：${error.localizedMessage}" else null,
                        )
                    }
                    mutableState.value.sessions.firstOrNull()?.let(::selectSession)
                }
        }
    }

    fun createSession() {
        if (!mutableState.value.isOnline) {
            mutableState.update { it.copy(error = "离线状态不能新建会话") }
            return
        }
        viewModelScope.launch {
            runCatching { repository.createSession(ownerId) }
                .onSuccess(::selectSession)
                .onFailure { mutableState.update { state -> state.copy(error = "新建会话失败") } }
        }
    }

    fun selectSession(session: ChatSession) {
        if (mutableState.value.activeSession?.id == session.id && messagesJob != null) return
        streamJob?.cancel()
        messagesJob?.cancel()
        mutableState.update {
            it.copy(
                activeSession = session,
                messages = emptyList(),
                isLoadingMessages = true,
                isSending = false,
                connectionLabel = "正在恢复会话",
                restoredWorkflow = null,
                restoredClarification = null,
                error = null,
            )
        }
        messagesJob = viewModelScope.launch {
            repository.observeMessages(ownerId, session.id).collect { messages ->
                if (!mutableState.value.isSending) {
                    mutableState.update { it.copy(messages = messages) }
                }
            }
        }
        viewModelScope.launch {
            runCatching { repository.restoreSession(ownerId, session.id) }
                .onSuccess { restore ->
                    mutableState.update { state ->
                        state.copy(
                            restoredWorkflow = restore.pendingWorkflow,
                            restoredClarification = restore.clarification,
                            isLoadingMessages = false,
                            connectionLabel = if (state.isOnline) "准备就绪" else "离线只读",
                            scrollRequest = state.scrollRequest + 1,
                        )
                    }
                }
                .onFailure {
                    mutableState.update { state ->
                        state.copy(
                            isLoadingMessages = false,
                            connectionLabel = if (state.messages.isEmpty()) "恢复失败" else "已显示本地缓存",
                            error = if (state.messages.isEmpty()) "无法恢复当前会话" else null,
                        )
                    }
                }
        }
    }

    fun send(
        textOverride: String? = null,
        clarification: ClarificationInputDto? = null,
    ) {
        val state = mutableState.value
        val text = (textOverride ?: state.composer).trim()
        val session = state.activeSession ?: return
        if (text.isEmpty() || state.isSending) return
        if (!state.isOnline) {
            mutableState.update { it.copy(error = "当前为离线只读状态，联网后才能发送") }
            return
        }

        val assistantId = "local-assistant-${UUID.randomUUID()}"
        val now = Instant.now().toString()
        mutableState.update {
            it.copy(
                composer = "",
                correctionPrefill = null,
                restoredWorkflow = if (text in DRAFT_ACTIONS) null else it.restoredWorkflow,
                restoredClarification = if (clarification != null) null else it.restoredClarification,
                isSending = true,
                requestStartedAt = System.currentTimeMillis(),
                firstTokenAt = null,
                connectionLabel = "正在理解你的需求",
                error = null,
                scrollRequest = it.scrollRequest + 1,
                messages = it.messages.map { message ->
                    if (clarification != null) message.copy(clarification = null) else message
                }.map { message ->
                    if (text in DRAFT_ACTIONS) message.copy(draft = null) else message
                } + listOf(
                    ChatMessage(
                        id = "local-user-${UUID.randomUUID()}", sessionId = session.id,
                        role = MessageRole.USER, content = text, createdAt = now,
                    ),
                    ChatMessage(
                        id = assistantId, sessionId = session.id, role = MessageRole.ASSISTANT,
                        content = "", createdAt = now, isStreaming = true,
                    ),
                ),
            )
        }

        streamJob = viewModelScope.launch {
            repository.streamMessage(session.threadId, text, clarification)
                .catch { error -> finishWithError(assistantId, error.localizedMessage ?: "连接中断") }
                .collect { event -> handleEvent(assistantId, event) }
        }
    }

    fun confirmDraft() = send("确认保存")
    fun cancelDraft() = send("取消保存")
    fun correctDraft(workflow: PendingWorkflow) = mutableState.update {
        it.copy(composer = workflow.actions.correctionPrefill, correctionPrefill = workflow.actions.correctionPrefill)
    }

    fun selectClarification(id: Long, intent: String, label: String) = send(
        textOverride = label,
        clarification = ClarificationInputDto(id, "select", intent),
    )

    fun cancelClarification(id: Long) = send(
        textOverride = "取消本次操作",
        clarification = ClarificationInputDto(id, "cancel"),
    )

    private fun handleEvent(assistantId: String, event: ChatStreamEvent) {
        when (event) {
            is ChatStreamEvent.IntentRecognized -> mutableState.update {
                it.copy(connectionLabel = "已识别 · ${event.intent}")
            }
            is ChatStreamEvent.SessionConnected -> Unit
            is ChatStreamEvent.AgentState -> updateAssistant(assistantId) { message ->
                message.copy(
                    trace = message.trace + AgentTraceStep(
                        event.workflow, event.status, event.node, event.title, event.detail,
                    ),
                )
            }.also { mutableState.update { it.copy(connectionLabel = event.title, scrollRequest = it.scrollRequest + 1) } }
            is ChatStreamEvent.Workflow -> {
                if (event.action in setOf("draft_created", "draft_updated") && event.draftId != null &&
                    event.draft != null && event.draftActions != null
                ) {
                    val pending = PendingWorkflow(
                        event.workflow, "", event.draftId, event.draft,
                        event.draftActions.toDomain(), Instant.now().toString(),
                    )
                    updateAssistant(assistantId) { it.copy(draft = pending) }
                }
            }
            is ChatStreamEvent.Clarification -> updateAssistant(assistantId) {
                it.copy(clarification = event.value.toDomain())
            }
            is ChatStreamEvent.Delta -> {
                updateAssistant(assistantId) { it.copy(content = it.content + event.content) }
                mutableState.update {
                    it.copy(
                        firstTokenAt = it.firstTokenAt ?: System.currentTimeMillis(),
                        connectionLabel = "正在回复",
                        scrollRequest = it.scrollRequest + 1,
                    )
                }
            }
            is ChatStreamEvent.Done -> {
                updateAssistant(assistantId) { message ->
                    message.copy(
                        content = message.content.ifBlank { event.reply },
                        isStreaming = false,
                    )
                }
                mutableState.update {
                    it.copy(isSending = false, connectionLabel = "已完成", scrollRequest = it.scrollRequest + 1)
                }
            }
            is ChatStreamEvent.Error -> finishWithError(assistantId, event.message)
            is ChatStreamEvent.Unknown -> Unit
        }
    }

    private fun updateAssistant(id: String, transform: (ChatMessage) -> ChatMessage) {
        mutableState.update { state ->
            state.copy(messages = state.messages.map { if (it.id == id) transform(it) else it })
        }
    }

    private fun finishWithError(assistantId: String, message: String) {
        updateAssistant(assistantId) {
            it.copy(content = it.content.ifBlank { "本次请求未完成，请稍后重试。" }, isStreaming = false)
        }
        mutableState.update { it.copy(isSending = false, connectionLabel = "连接异常", error = message) }
    }

    private companion object {
        val DRAFT_ACTIONS = setOf("确认保存", "取消保存")
    }
}
