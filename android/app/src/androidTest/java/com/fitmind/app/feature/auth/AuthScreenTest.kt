package com.fitmind.app.feature.auth

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.v2.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.fitmind.app.core.designsystem.FitMindTheme
import org.junit.Rule
import org.junit.Test

class AuthScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun switchesFromLoginToRegistrationFields() {
        var mode by mutableStateOf(AuthMode.LOGIN)
        composeRule.setContent {
            FitMindTheme {
                AuthScreen(
                    AuthUiState(status = AuthStatus.SignedOut, mode = mode),
                    AuthEventHandler(
                        mode = { mode = it },
                        identifier = {}, email = {}, username = {}, displayName = {}, password = {}, submit = {},
                    ),
                )
            }
        }
        composeRule.onNodeWithText("注册").performClick()
        composeRule.onNodeWithText("邮箱").assertIsDisplayed()
        composeRule.onNodeWithText("创建账号").assertIsDisplayed()
    }
}
