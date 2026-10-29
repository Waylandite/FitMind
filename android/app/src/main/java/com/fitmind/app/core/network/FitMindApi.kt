package com.fitmind.app.core.network

import com.fitmind.app.core.network.dto.AuthTokenResponseDto
import com.fitmind.app.core.network.dto.ChatSessionDto
import com.fitmind.app.core.network.dto.ClarificationDto
import com.fitmind.app.core.network.dto.ConversationLogDto
import com.fitmind.app.core.network.dto.CreateSessionRequestDto
import com.fitmind.app.core.network.dto.LoginRequestDto
import com.fitmind.app.core.network.dto.PendingWorkflowDto
import com.fitmind.app.core.network.dto.RegisterRequestDto
import com.fitmind.app.core.network.dto.UserDto
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface FitMindApi {
    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequestDto): AuthTokenResponseDto

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequestDto): AuthTokenResponseDto

    @POST("auth/refresh")
    suspend fun refresh(): AuthTokenResponseDto

    @POST("auth/logout")
    suspend fun logout(): Response<Unit>

    @GET("auth/me")
    suspend fun me(): UserDto

    @GET("memories/sessions")
    suspend fun sessions(): List<ChatSessionDto>

    @POST("memories/sessions")
    suspend fun createSession(@Body request: CreateSessionRequestDto): ChatSessionDto

    @GET("memories/sessions/{sessionId}/messages")
    suspend fun messages(@Path("sessionId") sessionId: Long): List<ConversationLogDto>

    @GET("memories/sessions/{sessionId}/clarification")
    suspend fun clarification(@Path("sessionId") sessionId: Long): ClarificationDto?

    @GET("memories/sessions/{sessionId}/pending-workflow")
    suspend fun pendingWorkflow(@Path("sessionId") sessionId: Long): PendingWorkflowDto?
}

interface RefreshApi {
    @POST("auth/refresh")
    suspend fun refresh(): AuthTokenResponseDto
}
