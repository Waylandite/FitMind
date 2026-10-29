package com.fitmind.app.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.fitmind.app.core.designsystem.FitMindTheme
import com.fitmind.app.feature.auth.AuthBootstrapScreen
import com.fitmind.app.feature.auth.AuthEventHandler
import com.fitmind.app.feature.auth.AuthScreen
import com.fitmind.app.feature.auth.AuthStatus
import com.fitmind.app.feature.auth.AuthViewModel
import com.fitmind.app.feature.chat.ChatScreen
import com.fitmind.app.feature.chat.ChatViewModel

private const val AUTH_ROUTE = "auth"
private const val CHAT_ROUTE = "chat"

@Composable
fun FitMindApp(authViewModel: AuthViewModel = hiltViewModel()) {
    val authState by authViewModel.state.collectAsStateWithLifecycle()
    FitMindTheme {
        if (authState.status == AuthStatus.Bootstrapping) {
            AuthBootstrapScreen()
            return@FitMindTheme
        }

        val navController = rememberNavController()
        val signedIn = authState.status is AuthStatus.SignedIn
        LaunchedEffect(signedIn) {
            val destination = if (signedIn) CHAT_ROUTE else AUTH_ROUTE
            navController.navigate(destination) {
                popUpTo(navController.graph.startDestinationId) { inclusive = true }
                launchSingleTop = true
            }
        }

        NavHost(
            navController = navController,
            startDestination = if (signedIn) CHAT_ROUTE else AUTH_ROUTE,
        ) {
            composable(AUTH_ROUTE) {
                AuthScreen(
                    authState,
                    AuthEventHandler(
                        mode = authViewModel::setMode,
                        identifier = authViewModel::setIdentifier,
                        email = authViewModel::setEmail,
                        username = authViewModel::setUsername,
                        displayName = authViewModel::setDisplayName,
                        password = authViewModel::setPassword,
                        submit = authViewModel::submit,
                    ),
                )
            }
            composable(CHAT_ROUTE) {
                val status = authState.status as? AuthStatus.SignedIn ?: return@composable
                val chatViewModel: ChatViewModel = hiltViewModel()
                val chatState by chatViewModel.state.collectAsStateWithLifecycle()
                ChatScreen(
                    state = chatState,
                    username = status.user.displayName ?: status.user.username,
                    onComposer = chatViewModel::setComposer,
                    onSend = { chatViewModel.send() },
                    onCreateSession = chatViewModel::createSession,
                    onSelectSession = chatViewModel::selectSession,
                    onConfirmDraft = chatViewModel::confirmDraft,
                    onCancelDraft = chatViewModel::cancelDraft,
                    onCorrectDraft = chatViewModel::correctDraft,
                    onSelectClarification = chatViewModel::selectClarification,
                    onCancelClarification = chatViewModel::cancelClarification,
                    onLogout = authViewModel::logout,
                    onClearError = chatViewModel::clearError,
                )
            }
        }
    }
}
