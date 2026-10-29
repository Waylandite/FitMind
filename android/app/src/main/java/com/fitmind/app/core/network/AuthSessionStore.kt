package com.fitmind.app.core.network

import com.fitmind.app.core.model.User
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

data class AuthSession(val accessToken: String, val user: User)

@Singleton
class AuthSessionStore @Inject constructor() {
    private val mutableSession = MutableStateFlow<AuthSession?>(null)
    val session: StateFlow<AuthSession?> = mutableSession.asStateFlow()

    fun set(accessToken: String, user: User) {
        mutableSession.value = AuthSession(accessToken, user)
    }

    fun clear() {
        mutableSession.value = null
    }
}
