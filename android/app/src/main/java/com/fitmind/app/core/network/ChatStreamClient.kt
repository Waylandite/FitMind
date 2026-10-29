package com.fitmind.app.core.network

import com.fitmind.app.core.network.dto.ChatRequestDto
import com.fitmind.app.core.network.dto.ClarificationDto
import java.io.IOException
import javax.inject.Inject
import javax.inject.Named
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

@Singleton
class ChatStreamClient @Inject constructor(
    private val client: OkHttpClient,
    private val json: Json,
    @param:Named("apiBaseUrl") private val baseUrl: String,
) {
    fun stream(request: ChatRequestDto): Flow<ChatStreamEvent> = flow {
        val body = json.encodeToString(ChatRequestDto.serializer(), request)
            .toRequestBody(JSON_MEDIA_TYPE)
        val call = client.newCall(
            Request.Builder()
                .url(baseUrl + "chat/stream")
                .post(body)
                .header("Accept", "text/event-stream")
                .build(),
        )
        val cancellationHandle = currentCoroutineContext()[Job]?.invokeOnCompletion { cause ->
            if (cause is CancellationException) call.cancel()
        }
        try {
            var terminalReceived = false
            call.execute().use { response ->
                if (!response.isSuccessful) throw IOException("对话连接失败 (${response.code})")
                val source = response.body.source()
                val dataLines = mutableListOf<String>()
                while (!source.exhausted()) {
                    currentCoroutineContext().ensureActive()
                    val line = source.readUtf8Line() ?: break
                    if (line.isBlank()) {
                        if (dataLines.isNotEmpty()) {
                            val event = decodeEvent(dataLines.joinToString("\n"))
                            terminalReceived = terminalReceived ||
                                event is ChatStreamEvent.Done || event is ChatStreamEvent.Error
                            emit(event)
                            dataLines.clear()
                        }
                    } else if (line.startsWith("data:")) {
                        dataLines += line.removePrefix("data:").trimStart()
                    }
                }
                if (dataLines.isNotEmpty()) {
                    val event = decodeEvent(dataLines.joinToString("\n"))
                    terminalReceived = terminalReceived ||
                        event is ChatStreamEvent.Done || event is ChatStreamEvent.Error
                    emit(event)
                }
                if (!terminalReceived) {
                    emit(ChatStreamEvent.Error("连接提前结束，请重试"))
                }
            }
        } catch (error: CancellationException) {
            call.cancel()
            throw error
        } finally {
            cancellationHandle?.dispose()
        }
    }.flowOn(Dispatchers.IO)

    internal fun decodeEvent(payload: String): ChatStreamEvent {
        val element = runCatching { json.parseToJsonElement(payload) }.getOrNull()
            ?: return ChatStreamEvent.Error("无法解析服务端流式消息")
        val type = element.jsonObject["type"]?.jsonPrimitive?.contentOrNull.orEmpty()
        if (type == "clarification") {
            return runCatching {
                ChatStreamEvent.Clarification(json.decodeFromJsonElement(ClarificationDto.serializer(), element))
            }.getOrElse { ChatStreamEvent.Error("意图澄清消息格式无效") }
        }
        val envelope = runCatching {
            json.decodeFromJsonElement(StreamEnvelope.serializer(), element)
        }.getOrElse { return ChatStreamEvent.Error("流式消息字段无效") }
        return when (type) {
            "intent" -> ChatStreamEvent.IntentRecognized(
                envelope.intent.orEmpty(), envelope.confidence ?: 0.0,
                envelope.source.orEmpty(), envelope.reason.orEmpty(),
            )
            "session" -> ChatStreamEvent.SessionConnected(
                envelope.threadId.orEmpty(), envelope.sessionId ?: 0L,
            )
            "agent_state" -> ChatStreamEvent.AgentState(
                element.jsonObject["workflow"]?.jsonPrimitive?.contentOrNull.orEmpty(),
                envelope.status.orEmpty(), envelope.node.orEmpty(),
                envelope.title.orEmpty(), envelope.detail.orEmpty(),
            )
            "workflow" -> ChatStreamEvent.Workflow(
                element.jsonObject["workflow"]?.jsonPrimitive?.contentOrNull.orEmpty(),
                envelope.action.orEmpty(), envelope.draftId,
                envelope.draft ?: envelope.payload, envelope.draftActions,
            )
            "delta" -> ChatStreamEvent.Delta(envelope.content.orEmpty())
            "done" -> ChatStreamEvent.Done(
                envelope.reply.orEmpty(), envelope.sessionId, envelope.intent,
                (envelope.workflow as? kotlinx.serialization.json.JsonObject)
                    ?.get("name")?.jsonPrimitive?.contentOrNull,
            )
            "error" -> ChatStreamEvent.Error(envelope.message ?: envelope.reply ?: "流式响应异常")
            else -> ChatStreamEvent.Unknown(type)
        }
    }

    private companion object {
        val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
    }
}
