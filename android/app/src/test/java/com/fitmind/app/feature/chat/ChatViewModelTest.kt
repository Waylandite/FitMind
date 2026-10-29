package com.fitmind.app.feature.chat

import com.fitmind.app.core.model.ChatMessage
import com.fitmind.app.core.model.ChatSession
import com.fitmind.app.core.model.User
import com.fitmind.app.core.network.AuthSessionStore
import com.fitmind.app.core.network.ChatStreamEvent
import com.fitmind.app.core.network.NetworkStatusProvider
import com.fitmind.app.core.network.dto.ClarificationInputDto
import com.fitmind.app.data.ChatRepositoryContract
import com.fitmind.app.data.SessionRestore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ChatViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `stream updates trace delta and completion in one assistant message`() = runTest(dispatcher) {
        val authStore = AuthSessionStore().apply {
            set("token", User(1, "a@b.com", "runner", null, null))
        }
        val repository = FakeChatRepository()
        val viewModel = ChatViewModel(repository, authStore, FakeNetworkMonitor())
        advanceUntilIdle()

        viewModel.setComposer("今天练什么")
        viewModel.send()
        advanceUntilIdle()

        val assistant = viewModel.state.value.messages.last()
        assertEquals("建议练腿", assistant.content)
        assertEquals("正在分析", assistant.trace.single().title)
        assertFalse(assistant.isStreaming)
        assertFalse(viewModel.state.value.isSending)
    }

    private class FakeNetworkMonitor : NetworkStatusProvider {
        override val isOnline = flowOf(true)
    }

    private class FakeChatRepository : ChatRepositoryContract {
        private val sessions = MutableStateFlow(listOf(SESSION))
        override fun observeSessions(ownerId: Long): Flow<List<ChatSession>> = sessions
        override fun observeMessages(ownerId: Long, sessionId: Long): Flow<List<ChatMessage>> = flowOf(emptyList())
        override suspend fun refreshSessions(ownerId: Long) = listOf(SESSION)
        override suspend fun createSession(ownerId: Long) = SESSION
        override suspend fun restoreSession(ownerId: Long, sessionId: Long) = SessionRestore(null, null)
        override fun streamMessage(
            threadId: String,
            message: String,
            clarification: ClarificationInputDto?,
        ): Flow<ChatStreamEvent> = flowOf(
            ChatStreamEvent.AgentState("today_workout_recommendation", "thinking", "query", "正在分析", "查询记录"),
            ChatStreamEvent.Delta("建议练腿"),
            ChatStreamEvent.Done("建议练腿", 1, "today_workout_recommendation", "today_workout_recommendation"),
        )
    }

    private companion object {
        val SESSION = ChatSession(1, "thread-1", "新的会话", "active", "2026-08-20T00:00:00Z", null)
    }
}
