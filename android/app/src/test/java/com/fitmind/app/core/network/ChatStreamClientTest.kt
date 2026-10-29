package com.fitmind.app.core.network

import com.fitmind.app.core.network.dto.ChatRequestDto
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatStreamClientTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `stream parses chinese deltas and done event`() = runTest {
        val server = MockWebServer()
        server.enqueue(
            MockResponse().setHeader("Content-Type", "text/event-stream").setBody(
                "data: {\"type\":\"delta\",\"content\":\"今天练腿\"}\n\n" +
                    "data: {\"type\":\"done\",\"reply\":\"今天练腿\",\"session_id\":7," +
                    "\"intent\":\"today_workout_recommendation\"," +
                    "\"workflow\":{\"name\":\"today_workout_recommendation\"}}\n\n",
            ),
        )
        server.start()
        try {
            val client = ChatStreamClient(
                OkHttpClient(), json, server.url("/api/v1/").toString(),
            )
            val events = client.stream(ChatRequestDto("thread-1", "今天练什么")).toList()

            assertEquals("今天练腿", (events[0] as ChatStreamEvent.Delta).content)
            val done = events[1] as ChatStreamEvent.Done
            assertEquals(7L, done.sessionId)
            assertEquals("today_workout_recommendation", done.workflow)
        } finally {
            server.shutdown()
        }
    }

    @Test
    fun `decoder safely keeps unknown event`() {
        val client = ChatStreamClient(OkHttpClient(), json, "https://example.com/api/v1/")
        val event = client.decodeEvent("{\"type\":\"future_event\",\"payload\":{}}")
        assertTrue(event is ChatStreamEvent.Unknown)
    }

    @Test
    fun `decoder maps workflow draft payload`() {
        val client = ChatStreamClient(OkHttpClient(), json, "https://example.com/api/v1/")
        val event = client.decodeEvent(
            """{"type":"workflow","workflow":"workout_record","action":"draft_created","draft_id":9,"draft":{"raw_text":"深蹲 3 组"},"draft_actions":{"label":"训练记录草稿","hint":"确认","confirm_text":"确认保存","cancel_text":"取消保存","correction_text":"纠正错误","correction_prefill":"请修改：深蹲 3 组"}}""",
        ) as ChatStreamEvent.Workflow

        assertEquals("workout_record", event.workflow)
        assertEquals(9L, event.draftId)
        assertEquals("训练记录草稿", event.draftActions?.label)
    }

    @Test
    fun `stream reports an error when server closes before terminal event`() = runTest {
        val server = MockWebServer()
        server.enqueue(
            MockResponse().setHeader("Content-Type", "text/event-stream").setBody(
                "data: {\"type\":\"delta\",\"content\":\"未完成\"}\n\n",
            ),
        )
        server.start()
        try {
            val client = ChatStreamClient(
                OkHttpClient(), json, server.url("/api/v1/").toString(),
            )

            val events = client.stream(ChatRequestDto("thread-1", "继续")).toList()

            assertEquals("未完成", (events[0] as ChatStreamEvent.Delta).content)
            assertEquals("连接提前结束，请重试", (events[1] as ChatStreamEvent.Error).message)
        } finally {
            server.shutdown()
        }
    }
}
