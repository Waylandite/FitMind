package com.fitmind.app.feature.auth

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.Mail
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fitmind.app.core.designsystem.FitBlue
import com.fitmind.app.core.designsystem.FitInk
import com.fitmind.app.core.designsystem.FitMint

@Composable
fun AuthBootstrapScreen() {
    Box(
        Modifier.fillMaxSize().background(
            Brush.linearGradient(listOf(FitInk, Color(0xFF173D46))),
        ),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            FitMindMark()
            Spacer(Modifier.height(22.dp))
            CircularProgressIndicator(color = FitMint, strokeWidth = 3.dp)
            Spacer(Modifier.height(14.dp))
            Text("正在恢复你的训练轨迹", color = Color.White.copy(alpha = 0.74f))
        }
    }
}

@Composable
fun AuthScreen(state: AuthUiState, onEvent: AuthEventHandler) {
    Box(
        Modifier.fillMaxSize().background(
            Brush.verticalGradient(
                0f to FitInk,
                0.48f to Color(0xFF17343B),
                1f to MaterialTheme.colorScheme.background,
            ),
        ),
    ) {
        Column(
            modifier = Modifier.fillMaxSize().padding(horizontal = 22.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(58.dp))
            FitMindMark()
            Spacer(Modifier.height(20.dp))
            Text(
                "训练被看见，状态被记住。",
                color = Color.White,
                style = MaterialTheme.typography.headlineMedium,
            )
            Text(
                "你的长期健身智能体",
                color = FitMint,
                modifier = Modifier.padding(top = 7.dp),
                letterSpacing = 2.sp,
            )
            Spacer(Modifier.height(34.dp))

            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(30.dp),
                color = MaterialTheme.colorScheme.surface,
                tonalElevation = 8.dp,
                shadowElevation = 18.dp,
            ) {
                Column(Modifier.padding(22.dp)) {
                    ModeSwitch(state.mode, onEvent.mode)
                    Spacer(Modifier.height(22.dp))
                    AnimatedContent(
                        targetState = state.mode,
                        transitionSpec = {
                            (slideInHorizontally(tween(260)) { it / 3 } + fadeIn()) togetherWith
                                (slideOutHorizontally(tween(220)) { -it / 3 } + fadeOut())
                        },
                        label = "auth-form",
                    ) { mode ->
                        Column(verticalArrangement = Arrangement.spacedBy(13.dp)) {
                            if (mode == AuthMode.LOGIN) {
                                AuthField(
                                    state.identifier, onEvent.identifier,
                                    "邮箱或用户名", Icons.Rounded.Person,
                                )
                            } else {
                                AuthField(
                                    state.email, onEvent.email, "邮箱", Icons.Rounded.Mail,
                                    keyboardType = KeyboardType.Email,
                                )
                                AuthField(
                                    state.username, onEvent.username, "用户名", Icons.Rounded.Person,
                                )
                                AuthField(
                                    state.displayName, onEvent.displayName, "显示名称（可选）", Icons.Rounded.Person,
                                )
                            }
                            AuthField(
                                state.password,
                                onEvent.password,
                                "密码",
                                Icons.Rounded.Lock,
                                password = true,
                                imeAction = ImeAction.Done,
                                onDone = onEvent.submit,
                            )
                        }
                    }

                    if (state.error != null) {
                        Text(
                            state.error,
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.padding(top = 13.dp),
                        )
                    }
                    Spacer(Modifier.height(18.dp))
                    Button(
                        onClick = onEvent.submit,
                        enabled = !state.isSubmitting,
                        modifier = Modifier.fillMaxWidth().height(56.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = FitInk),
                        shape = RoundedCornerShape(18.dp),
                    ) {
                        if (state.isSubmitting) {
                            CircularProgressIndicator(Modifier.size(22.dp), color = FitMint, strokeWidth = 2.dp)
                        } else {
                            Text(if (state.mode == AuthMode.LOGIN) "进入 FitMind" else "创建账号")
                        }
                    }
                }
            }
            Spacer(Modifier.weight(1f))
            Text(
                "FITMIND · MEMORY-DRIVEN FITNESS",
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.48f),
                style = MaterialTheme.typography.labelLarge,
                letterSpacing = 1.6.sp,
                modifier = Modifier.padding(bottom = 24.dp),
            )
        }
    }
}

@Composable
private fun ModeSwitch(mode: AuthMode, onMode: (AuthMode) -> Unit) {
    Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
        Row(Modifier.fillMaxWidth().padding(4.dp)) {
            AuthMode.entries.forEach { item ->
                val selected = item == mode
                val color by animateColorAsState(
                    if (selected) FitInk else Color.Transparent,
                    spring(), label = "mode-color",
                )
                TextButton(
                    onClick = { onMode(item) },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(13.dp),
                    colors = ButtonDefaults.textButtonColors(containerColor = color),
                ) {
                    Text(
                        if (item == AuthMode.LOGIN) "登录" else "注册",
                        color = if (selected) Color.White else MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
        }
    }
}

@Composable
private fun AuthField(
    value: String,
    onValue: (String) -> Unit,
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    keyboardType: KeyboardType = KeyboardType.Text,
    password: Boolean = false,
    imeAction: ImeAction = ImeAction.Next,
    onDone: () -> Unit = {},
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValue,
        modifier = Modifier.fillMaxWidth(),
        label = { Text(label) },
        leadingIcon = { Icon(icon, null) },
        visualTransformation = if (password) PasswordVisualTransformation() else androidx.compose.ui.text.input.VisualTransformation.None,
        singleLine = true,
        shape = RoundedCornerShape(17.dp),
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType, imeAction = imeAction),
        keyboardActions = KeyboardActions(onDone = { onDone() }),
    )
}

@Composable
private fun FitMindMark() {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            Modifier.size(42.dp).clip(CircleShape).background(
                Brush.linearGradient(listOf(FitBlue, FitMint)),
            ),
            contentAlignment = Alignment.Center,
        ) {
            Text("F", color = Color.White, fontWeight = FontWeight.Black, fontSize = 21.sp)
        }
        Column(Modifier.padding(start = 12.dp)) {
            Text("FITMIND", color = Color.White, fontWeight = FontWeight.Bold, letterSpacing = 3.sp)
            Text("HEALTH INTELLIGENCE", color = Color.White.copy(alpha = 0.5f), fontSize = 9.sp, letterSpacing = 1.2.sp)
        }
    }
}

data class AuthEventHandler(
    val mode: (AuthMode) -> Unit,
    val identifier: (String) -> Unit,
    val email: (String) -> Unit,
    val username: (String) -> Unit,
    val displayName: (String) -> Unit,
    val password: (String) -> Unit,
    val submit: () -> Unit,
)
