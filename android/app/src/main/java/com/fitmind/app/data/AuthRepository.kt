package com.fitmind.app.data

import com.fitmind.app.core.database.FitMindDao
import com.fitmind.app.core.model.User
import com.fitmind.app.core.network.AuthSessionStore
import com.fitmind.app.core.network.AuthSession
import com.fitmind.app.core.network.FitMindApi
import com.fitmind.app.core.network.SecureRefreshCookieJar
import com.fitmind.app.core.network.dto.LoginRequestDto
import com.fitmind.app.core.network.dto.RegisterRequestDto
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.StateFlow

interface AuthRepositoryContract {
    val session: StateFlow<AuthSession?>
    suspend fun bootstrap(): User?
    suspend fun login(identifier: String, password: String): User
    suspend fun register(email: String, username: String, password: String, displayName: String?): User
    suspend fun logout()
}

@Singleton
class AuthRepository @Inject constructor(
    private val api: FitMindApi,
    private val sessionStore: AuthSessionStore,
    private val cookieJar: SecureRefreshCookieJar,
    private val dao: FitMindDao,
) : AuthRepositoryContract {
    override val session = sessionStore.session

    override suspend fun bootstrap(): User? = runCatching {
        val refreshed = api.refresh()
        sessionStore.set(refreshed.accessToken, refreshed.user.toDomain())
        val user = api.me().toDomain()
        sessionStore.set(refreshed.accessToken, user)
        user
    }.onFailure {
        sessionStore.clear()
        cookieJar.clear()
    }.getOrNull()

    override suspend fun login(identifier: String, password: String): User {
        val response = api.login(LoginRequestDto(identifier.trim(), password))
        return response.user.toDomain().also { sessionStore.set(response.accessToken, it) }
    }

    override suspend fun register(
        email: String,
        username: String,
        password: String,
        displayName: String?,
    ): User {
        val response = api.register(
            RegisterRequestDto(email.trim().lowercase(), username.trim(), password, displayName?.trim()),
        )
        return response.user.toDomain().also { sessionStore.set(response.accessToken, it) }
    }

    override suspend fun logout() {
        val ownerId = sessionStore.session.value?.user?.id
        runCatching { api.logout() }
        sessionStore.clear()
        cookieJar.clear()
        if (ownerId != null) {
            dao.deleteSessions(ownerId)
            dao.deleteAllMessages(ownerId)
        }
    }
}
