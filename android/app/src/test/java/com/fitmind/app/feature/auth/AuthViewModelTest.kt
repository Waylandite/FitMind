package com.fitmind.app.feature.auth

import com.fitmind.app.core.model.User
import com.fitmind.app.data.AuthRepositoryContract
import com.fitmind.app.core.network.AuthSession
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
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
class AuthViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `bootstrap failure leads to signed out without exposing error`() = runTest(dispatcher) {
        val viewModel = AuthViewModel(FakeAuthRepository())
        advanceUntilIdle()
        assertEquals(AuthStatus.SignedOut, viewModel.state.value.status)
    }

    @Test
    fun `register validates password before network call`() = runTest(dispatcher) {
        val repository = FakeAuthRepository()
        val viewModel = AuthViewModel(repository)
        advanceUntilIdle()
        viewModel.setMode(AuthMode.REGISTER)
        viewModel.setEmail("user@example.com")
        viewModel.setUsername("runner")
        viewModel.setPassword("short")
        viewModel.submit()
        advanceUntilIdle()

        assertEquals("密码需要 8-128 位", viewModel.state.value.error)
        assertFalse(repository.registerCalled)
    }

    private class FakeAuthRepository : AuthRepositoryContract {
        var registerCalled = false
        override val session: StateFlow<AuthSession?> = MutableStateFlow(null)
        override suspend fun bootstrap(): User? = null
        override suspend fun login(identifier: String, password: String) = USER
        override suspend fun register(
            email: String,
            username: String,
            password: String,
            displayName: String?,
        ): User {
            registerCalled = true
            return USER
        }
        override suspend fun logout() = Unit
    }

    private companion object {
        val USER = User(1, "user@example.com", "runner", null, null)
    }
}
