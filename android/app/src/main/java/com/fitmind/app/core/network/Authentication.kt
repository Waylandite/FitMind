package com.fitmind.app.core.network

import dagger.Lazy
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okhttp3.Authenticator
import okhttp3.Interceptor
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

class AccessTokenInterceptor @Inject constructor(
    private val sessionStore: AuthSessionStore,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val token = sessionStore.session.value?.accessToken
        val request = if (token == null) chain.request() else chain.request().newBuilder()
            .header("Authorization", "Bearer $token")
            .build()
        return chain.proceed(request)
    }
}

@Singleton
class RefreshCoordinator @Inject constructor(
    private val refreshApi: RefreshApi,
    private val sessionStore: AuthSessionStore,
    private val cookieJar: SecureRefreshCookieJar,
) {
    private val mutex = Mutex()

    suspend fun refresh(failedToken: String?): String? = mutex.withLock {
        val current = sessionStore.session.value
        if (current != null && failedToken != null && current.accessToken != failedToken) {
            return@withLock current.accessToken
        }
        runCatching { refreshApi.refresh() }
            .onSuccess { sessionStore.set(it.accessToken, it.user.toDomain()) }
            .onFailure {
                sessionStore.clear()
                cookieJar.clear()
            }
            .getOrNull()
            ?.accessToken
    }
}

class AccessTokenAuthenticator @Inject constructor(
    private val coordinator: Lazy<RefreshCoordinator>,
) : Authenticator {
    override fun authenticate(route: Route?, response: Response): Request? {
        if (response.request.url.encodedPath in PUBLIC_AUTH_PATHS) return null
        if (response.retryCount() >= 2) return null
        val failedToken = response.request.header("Authorization")?.removePrefix("Bearer ")
        val token = runBlocking { coordinator.get().refresh(failedToken) } ?: return null
        return response.request.newBuilder()
            .header("Authorization", "Bearer $token")
            .build()
    }

    private fun Response.retryCount(): Int {
        var count = 1
        var current = priorResponse
        while (current != null) {
            count += 1
            current = current.priorResponse
        }
        return count
    }

    private companion object {
        val PUBLIC_AUTH_PATHS = setOf(
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        )
    }
}
