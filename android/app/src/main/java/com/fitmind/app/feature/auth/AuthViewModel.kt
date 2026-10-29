package com.fitmind.app.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fitmind.app.core.model.User
import com.fitmind.app.data.AuthRepositoryContract
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.launch
import retrofit2.HttpException

enum class AuthMode { LOGIN, REGISTER }

sealed interface AuthStatus {
    data object Bootstrapping : AuthStatus
    data object SignedOut : AuthStatus
    data class SignedIn(val user: User) : AuthStatus
}

data class AuthUiState(
    val status: AuthStatus = AuthStatus.Bootstrapping,
    val mode: AuthMode = AuthMode.LOGIN,
    val identifier: String = "",
    val email: String = "",
    val username: String = "",
    val displayName: String = "",
    val password: String = "",
    val isSubmitting: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val repository: AuthRepositoryContract,
) : ViewModel() {
    private val mutableState = MutableStateFlow(AuthUiState())
    val state: StateFlow<AuthUiState> = mutableState.asStateFlow()

    init {
        viewModelScope.launch {
            repository.session.drop(1).collect { session ->
                mutableState.update { state ->
                    when {
                        session != null -> state.copy(status = AuthStatus.SignedIn(session.user))
                        state.status is AuthStatus.SignedIn -> AuthUiState(status = AuthStatus.SignedOut)
                        else -> state
                    }
                }
            }
        }
        viewModelScope.launch {
            val user = repository.bootstrap()
            mutableState.update { it.copy(status = user?.let(AuthStatus::SignedIn) ?: AuthStatus.SignedOut) }
        }
    }

    fun setMode(mode: AuthMode) = mutableState.update { it.copy(mode = mode, error = null) }
    fun setIdentifier(value: String) = mutableState.update { it.copy(identifier = value, error = null) }
    fun setEmail(value: String) = mutableState.update { it.copy(email = value, error = null) }
    fun setUsername(value: String) = mutableState.update { it.copy(username = value, error = null) }
    fun setDisplayName(value: String) = mutableState.update { it.copy(displayName = value, error = null) }
    fun setPassword(value: String) = mutableState.update { it.copy(password = value, error = null) }

    fun submit() {
        val current = mutableState.value
        val validation = validate(current)
        if (validation != null) {
            mutableState.update { it.copy(error = validation) }
            return
        }
        viewModelScope.launch {
            mutableState.update { it.copy(isSubmitting = true, error = null) }
            runCatching {
                if (current.mode == AuthMode.LOGIN) {
                    repository.login(current.identifier, current.password)
                } else {
                    repository.register(
                        current.email, current.username, current.password,
                        current.displayName.ifBlank { null },
                    )
                }
            }.onSuccess { user ->
                mutableState.update { it.copy(status = AuthStatus.SignedIn(user), isSubmitting = false) }
            }.onFailure { error ->
                mutableState.update {
                    it.copy(isSubmitting = false, error = error.userMessage())
                }
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
            mutableState.value = AuthUiState(status = AuthStatus.SignedOut)
        }
    }

    private fun validate(state: AuthUiState): String? {
        if (state.password.length !in 8..128 && state.mode == AuthMode.REGISTER) return "密码需要 8-128 位"
        if (state.password.isBlank()) return "请输入密码"
        if (state.mode == AuthMode.LOGIN && state.identifier.isBlank()) return "请输入邮箱或用户名"
        if (state.mode == AuthMode.REGISTER && !EMAIL.matches(state.email.trim())) return "请输入有效邮箱"
        if (state.mode == AuthMode.REGISTER && state.username.trim().length !in 3..20) return "用户名需要 3-20 位"
        return null
    }

    private fun Throwable.userMessage(): String = when (this) {
        is HttpException -> when (code()) {
            401 -> "账号或密码不正确"
            409 -> "邮箱或用户名已被使用"
            else -> "服务暂时不可用 (${code()})"
        }
        else -> "无法连接 FitMind，请检查网络"
    }

    private companion object {
        val EMAIL = Regex("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")
    }
}
