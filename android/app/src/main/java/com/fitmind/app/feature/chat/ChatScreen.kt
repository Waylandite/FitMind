package com.fitmind.app.feature.chat

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.automirrored.rounded.Send
import androidx.compose.material.icons.automirrored.rounded.Logout
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Edit
import androidx.compose.material.icons.rounded.ErrorOutline
import androidx.compose.material.icons.rounded.ExpandMore
import androidx.compose.material.icons.rounded.HourglassTop
import androidx.compose.material.icons.rounded.KeyboardArrowDown
import androidx.compose.material.icons.rounded.Menu
import androidx.compose.material.icons.rounded.Psychology
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fitmind.app.core.designsystem.FitBlue
import com.fitmind.app.core.designsystem.FitInk
import com.fitmind.app.core.designsystem.FitMint
import com.fitmind.app.core.model.AgentTraceStep
import com.fitmind.app.core.model.ChatMessage
import com.fitmind.app.core.model.ChatSession
import com.fitmind.app.core.model.Clarification
import com.fitmind.app.core.model.MessageRole
import com.fitmind.app.core.model.PendingWorkflow
import com.mikepenz.markdown.m3.Markdown
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    state: ChatUiState,
    username: String,
    onComposer: (String) -> Unit,
    onSend: () -> Unit,
    onCreateSession: () -> Unit,
    onSelectSession: (ChatSession) -> Unit,
    onConfirmDraft: () -> Unit,
    onCancelDraft: () -> Unit,
    onCorrectDraft: (PendingWorkflow) -> Unit,
    onSelectClarification: (Long, String, String) -> Unit,
    onCancelClarification: (Long) -> Unit,
    onLogout: () -> Unit,
    onClearError: () -> Unit,
) {
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(state.error) {
        state.error?.let {
            snackbar.showSnackbar(it)
            onClearError()
        }
    }

    BoxWithConstraints(Modifier.fillMaxSize()) {
        val expanded = maxWidth >= 840.dp
        if (expanded) {
            Row(Modifier.fillMaxSize()) {
                SessionPanel(
                    state, username, onCreateSession, onSelectSession, onLogout,
                    modifier = Modifier.width(310.dp).fillMaxHeight(),
                )
                ChatPane(
                    state, snackbar, showMenu = false, onMenu = {}, onComposer, onSend,
                    onConfirmDraft, onCancelDraft, onCorrectDraft,
                    onSelectClarification, onCancelClarification,
                    modifier = Modifier.weight(1f),
                )
            }
        } else {
            ModalNavigationDrawer(
                drawerState = drawerState,
                drawerContent = {
                    ModalDrawerSheet(drawerContainerColor = MaterialTheme.colorScheme.surface) {
                        SessionPanel(
                            state, username, onCreateSession,
                            onSelectSession = {
                                onSelectSession(it)
                                scope.launch { drawerState.close() }
                            },
                            onLogout = onLogout,
                            modifier = Modifier.fillMaxHeight().width(310.dp),
                        )
                    }
                },
            ) {
                ChatPane(
                    state, snackbar, showMenu = true,
                    onMenu = { scope.launch { drawerState.open() } },
                    onComposer, onSend, onConfirmDraft, onCancelDraft, onCorrectDraft,
                    onSelectClarification, onCancelClarification,
                    modifier = Modifier.fillMaxSize(),
                )
            }
        }
    }
}

@Composable
private fun SessionPanel(
    state: ChatUiState,
    username: String,
    onCreateSession: () -> Unit,
    onSelectSession: (ChatSession) -> Unit,
    onLogout: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier.background(
            Brush.verticalGradient(listOf(FitInk, Color(0xFF112D35))),
        ).statusBarsPadding().padding(18.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(42.dp).clip(CircleShape)
                    .background(Brush.linearGradient(listOf(FitBlue, FitMint))),
                contentAlignment = Alignment.Center,
            ) { Text("F", color = Color.White, fontWeight = FontWeight.Black, fontSize = 20.sp) }
            Column(Modifier.padding(start = 11.dp)) {
                Text("FITMIND", color = Color.White, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)
                Text("TRAINING MEMORY", color = Color.White.copy(alpha = 0.48f), fontSize = 9.sp)
            }
        }
        FilledTonalButton(
            onClick = onCreateSession,
            enabled = state.isOnline,
            modifier = Modifier.fillMaxWidth().padding(top = 24.dp),
            colors = ButtonDefaults.filledTonalButtonColors(
                containerColor = FitMint.copy(alpha = 0.16f), contentColor = FitMint,
            ),
        ) {
            Icon(Icons.Rounded.Add, null)
            Text("新建会话", Modifier.padding(start = 8.dp))
        }
        Text(
            "最近会话", color = Color.White.copy(alpha = 0.45f),
            style = MaterialTheme.typography.labelLarge,
            modifier = Modifier.padding(top = 25.dp, bottom = 10.dp),
        )
        if (state.isLoadingSessions) {
            CircularProgressIndicator(Modifier.size(22.dp), color = FitMint, strokeWidth = 2.dp)
        }
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            items(state.sessions, key = { it.id }) { session ->
                val selected = state.activeSession?.id == session.id
                Surface(
                    onClick = { onSelectSession(session) },
                    shape = RoundedCornerShape(15.dp),
                    color = if (selected) Color.White.copy(alpha = 0.13f) else Color.Transparent,
                ) {
                    Row(Modifier.fillMaxWidth().padding(13.dp), verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            Modifier.size(7.dp).clip(CircleShape)
                                .background(if (selected) FitMint else Color.White.copy(alpha = 0.24f)),
                        )
                        Text(
                            session.title ?: "新的会话",
                            color = Color.White.copy(alpha = if (selected) 0.96f else 0.68f),
                            modifier = Modifier.padding(start = 11.dp),
                            maxLines = 1,
                        )
                    }
                }
            }
        }
        HorizontalDivider(color = Color.White.copy(alpha = 0.1f))
        Row(
            Modifier.fillMaxWidth().padding(top = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                Modifier.size(36.dp).clip(CircleShape).background(Color.White.copy(alpha = 0.1f)),
                contentAlignment = Alignment.Center,
            ) { Text(username.take(1).uppercase(), color = FitMint, fontWeight = FontWeight.Bold) }
            Text(username, color = Color.White, modifier = Modifier.padding(start = 10.dp).weight(1f))
            IconButton(onClick = onLogout) { Icon(Icons.AutoMirrored.Rounded.Logout, "退出登录", tint = Color.White.copy(alpha = 0.68f)) }
        }
    }
}

@Composable
private fun ChatPane(
    state: ChatUiState,
    snackbar: SnackbarHostState,
    showMenu: Boolean,
    onMenu: () -> Unit,
    onComposer: (String) -> Unit,
    onSend: () -> Unit,
    onConfirmDraft: () -> Unit,
    onCancelDraft: () -> Unit,
    onCorrectDraft: (PendingWorkflow) -> Unit,
    onSelectClarification: (Long, String, String) -> Unit,
    onCancelClarification: (Long) -> Unit,
    modifier: Modifier,
) {
    Scaffold(
        modifier = modifier,
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            Row(
                Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                if (showMenu) IconButton(onClick = onMenu) { Icon(Icons.Rounded.Menu, "会话列表") }
                Column(Modifier.weight(1f)) {
                    Text(
                        state.activeSession?.title ?: "新的会话",
                        style = MaterialTheme.typography.titleLarge,
                    )
                    Text(
                        if (state.isOnline) state.connectionLabel else "离线只读",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (state.isOnline) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.error,
                    )
                }
                Box(
                    Modifier.size(9.dp).clip(CircleShape)
                        .background(if (state.isOnline) FitMint else MaterialTheme.colorScheme.error),
                )
            }
        },
        bottomBar = {
            ChatComposer(
                value = state.composer,
                enabled = state.isOnline && !state.isSending,
                onValue = onComposer,
                onSend = onSend,
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
    ) { padding ->
        MessageList(
            state, padding, onConfirmDraft, onCancelDraft, onCorrectDraft,
            onSelectClarification, onCancelClarification,
        )
    }
}

@Composable
private fun MessageList(
    state: ChatUiState,
    padding: PaddingValues,
    onConfirmDraft: () -> Unit,
    onCancelDraft: () -> Unit,
    onCorrectDraft: (PendingWorkflow) -> Unit,
    onSelectClarification: (Long, String, String) -> Unit,
    onCancelClarification: (Long) -> Unit,
) {
    val listState = rememberLazyListState()
    var followLatest by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()
    val itemCount = state.messages.size +
        if (state.restoredWorkflow != null || state.restoredClarification != null) 1 else 0
    val canScrollDown by remember {
        derivedStateOf { listState.canScrollForward }
    }
    val scrollObserver = remember {
        object : NestedScrollConnection {
            override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
                if (source == NestedScrollSource.UserInput && available.y > 0f) followLatest = false
                return Offset.Zero
            }
        }
    }

    LaunchedEffect(state.isSending) {
        if (state.isSending) followLatest = true
    }
    LaunchedEffect(state.scrollRequest, itemCount) {
        if (followLatest && itemCount > 0) listState.scrollToItem(itemCount - 1)
    }
    LaunchedEffect(canScrollDown) {
        if (!canScrollDown) followLatest = true
    }

    Box(Modifier.fillMaxSize().padding(padding)) {
        if (state.isLoadingMessages && state.messages.isEmpty()) {
            CircularProgressIndicator(Modifier.align(Alignment.Center), color = FitBlue)
        } else if (state.messages.isEmpty() && state.restoredWorkflow == null && state.restoredClarification == null) {
            EmptyConversation(Modifier.align(Alignment.Center))
        }
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize().nestedScroll(scrollObserver),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            items(state.messages, key = { it.id }) { message ->
                MessageRow(
                    message, state.requestStartedAt, state.firstTokenAt,
                    onConfirmDraft, onCancelDraft, onCorrectDraft,
                    onSelectClarification, onCancelClarification,
                )
            }
            if (state.restoredWorkflow != null || state.restoredClarification != null) {
                item(key = "restored-action") {
                    Column(Modifier.fillMaxWidth(0.9f)) {
                        Text("待处理", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.secondary)
                        state.restoredWorkflow?.let {
                            DraftCard(it, state.isSending, onConfirmDraft, onCancelDraft, onCorrectDraft)
                        }
                        state.restoredClarification?.let {
                            ClarificationCard(it, state.isSending, onSelectClarification, onCancelClarification)
                        }
                    }
                }
            }
            item { Spacer(Modifier.height(4.dp)) }
        }
        AnimatedVisibility(
            visible = !followLatest && canScrollDown,
            enter = fadeIn() + slideInVertically { it / 2 },
            exit = fadeOut() + slideOutVertically { it / 2 },
            modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 12.dp),
        ) {
            FilledTonalButton(onClick = {
                followLatest = true
                scope.launch { if (itemCount > 0) listState.animateScrollToItem(itemCount - 1) }
            }) {
                Icon(Icons.Rounded.KeyboardArrowDown, null)
                Text("回到最新", Modifier.padding(start = 6.dp))
            }
        }
    }
}

@Composable
private fun MessageRow(
    message: ChatMessage,
    requestStartedAt: Long?,
    firstTokenAt: Long?,
    onConfirmDraft: () -> Unit,
    onCancelDraft: () -> Unit,
    onCorrectDraft: (PendingWorkflow) -> Unit,
    onSelectClarification: (Long, String, String) -> Unit,
    onCancelClarification: (Long) -> Unit,
) {
    val user = message.role == MessageRole.USER
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = if (user) Arrangement.End else Arrangement.Start,
        verticalAlignment = Alignment.Top,
    ) {
        if (!user) AssistantAvatar()
        Column(
            Modifier.padding(start = if (user) 0.dp else 10.dp, end = if (user) 0.dp else 26.dp)
                .widthIn(max = 760.dp)
                .fillMaxWidth(if (user) 0.82f else 0.94f),
            horizontalAlignment = if (user) Alignment.End else Alignment.Start,
        ) {
            if (!user && message.trace.isNotEmpty()) AgentThoughtProcess(message.trace)
            Surface(
                shape = if (user) RoundedCornerShape(23.dp, 23.dp, 7.dp, 23.dp) else RoundedCornerShape(7.dp, 23.dp, 23.dp, 23.dp),
                color = if (user) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface,
                tonalElevation = if (user) 0.dp else 2.dp,
                shadowElevation = if (user) 0.dp else 1.dp,
            ) {
                Box(Modifier.padding(horizontal = 17.dp, vertical = 13.dp)) {
                    if (message.isStreaming && message.content.isEmpty()) {
                        ThinkingIndicator(requestStartedAt, firstTokenAt)
                    } else if (user) {
                        Text(message.content, style = MaterialTheme.typography.bodyLarge)
                    } else {
                        Markdown(message.content)
                    }
                }
            }
            message.draft?.let {
                DraftCard(it, message.isStreaming, onConfirmDraft, onCancelDraft, onCorrectDraft)
            }
            message.clarification?.let {
                ClarificationCard(it, message.isStreaming, onSelectClarification, onCancelClarification)
            }
        }
    }
}

@Composable
private fun AssistantAvatar() {
    Box(
        Modifier.size(38.dp).clip(CircleShape).background(
            Brush.linearGradient(listOf(FitBlue.copy(alpha = 0.18f), FitMint.copy(alpha = 0.22f))),
        ),
        contentAlignment = Alignment.Center,
    ) { Icon(Icons.Rounded.AutoAwesome, null, tint = FitBlue, modifier = Modifier.size(19.dp)) }
}

@Composable
private fun ThinkingIndicator(startedAt: Long?, firstTokenAt: Long?) {
    var now by remember(startedAt) { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(startedAt, firstTokenAt) {
        while (startedAt != null && firstTokenAt == null) {
            now = System.currentTimeMillis()
            delay(200)
        }
    }
    val transition = rememberInfiniteTransition(label = "thinking")
    val rotation by transition.animateFloat(
        0f, 180f,
        infiniteRepeatable(tween(900, easing = LinearEasing), RepeatMode.Restart),
        label = "hourglass",
    )
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(Icons.Rounded.HourglassTop, null, Modifier.size(20.dp).rotate(rotation), tint = FitBlue)
        Text(
            "正在思考 ${((firstTokenAt ?: now) - (startedAt ?: now)).coerceAtLeast(0) / 1000.0f}s",
            modifier = Modifier.padding(start = 9.dp),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun AgentThoughtProcess(steps: List<AgentTraceStep>) {
    var expanded by remember { mutableStateOf(false) }
    Card(
        onClick = { expanded = !expanded },
        modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.42f)),
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(Modifier.padding(13.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.Psychology, null, tint = MaterialTheme.colorScheme.secondary)
                Text(
                    "思考过程 · ${steps.size} 步",
                    modifier = Modifier.padding(start = 8.dp).weight(1f),
                    fontWeight = FontWeight.SemiBold,
                )
                Icon(Icons.Rounded.ExpandMore, null, Modifier.rotate(if (expanded) 180f else 0f))
            }
            AnimatedVisibility(expanded) {
                Column(Modifier.padding(top = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    steps.forEachIndexed { index, step ->
                        Row(verticalAlignment = Alignment.Top) {
                            Icon(
                                when (step.status) {
                                    "success" -> Icons.Rounded.Check
                                    "error" -> Icons.Rounded.ErrorOutline
                                    else -> Icons.Rounded.Refresh
                                },
                                null,
                                Modifier.size(17.dp),
                                tint = if (step.status == "error") MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.secondary,
                            )
                            Column(Modifier.padding(start = 9.dp)) {
                                Text(step.title, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyMedium)
                                if (step.detail.isNotBlank()) {
                                    Text(step.detail, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DraftCard(
    draft: PendingWorkflow,
    disabled: Boolean,
    onConfirm: () -> Unit,
    onCancel: () -> Unit,
    onCorrect: (PendingWorkflow) -> Unit,
) {
    Card(
        Modifier.fillMaxWidth().padding(top = 9.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.52f)),
        shape = RoundedCornerShape(18.dp),
    ) {
        Column(Modifier.padding(15.dp)) {
            Text(draft.actions.label, fontWeight = FontWeight.Bold)
            Text(
                draft.actions.correctionPrefill.substringAfter("：", draft.actions.hint),
                modifier = Modifier.padding(top = 6.dp),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodyMedium,
            )
            Row(Modifier.fillMaxWidth().padding(top = 13.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onConfirm, enabled = !disabled, modifier = Modifier.weight(1f)) {
                    Icon(Icons.Rounded.Check, null, Modifier.size(17.dp))
                    Text(draft.actions.confirmText, Modifier.padding(start = 5.dp))
                }
                OutlinedButton(onClick = onCancel, enabled = !disabled) {
                    Icon(Icons.Rounded.Close, null, Modifier.size(17.dp))
                }
                OutlinedButton(onClick = { onCorrect(draft) }, enabled = !disabled) {
                    Icon(Icons.Rounded.Edit, null, Modifier.size(17.dp))
                }
            }
        }
    }
}

@Composable
private fun ClarificationCard(
    clarification: Clarification,
    disabled: Boolean,
    onSelect: (Long, String, String) -> Unit,
    onCancel: (Long) -> Unit,
) {
    Card(
        Modifier.fillMaxWidth().padding(top = 9.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.55f)),
        shape = RoundedCornerShape(18.dp),
    ) {
        Column(Modifier.padding(15.dp)) {
            Text("需要确认你的意图", fontWeight = FontWeight.Bold)
            Text(clarification.question, Modifier.padding(top = 5.dp), style = MaterialTheme.typography.bodyMedium)
            clarification.options.forEach { option ->
                FilledTonalButton(
                    onClick = { onSelect(clarification.id, option.intent, option.label) },
                    enabled = !disabled && clarification.status == "pending",
                    modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                ) {
                    Column(Modifier.fillMaxWidth()) {
                        Text(option.label, fontWeight = FontWeight.SemiBold)
                        if (option.description.isNotBlank()) Text(option.description, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
            TextButton(
                onClick = { onCancel(clarification.id) },
                enabled = !disabled && clarification.status == "pending",
                modifier = Modifier.align(Alignment.End),
            ) { Text("取消本次操作", color = MaterialTheme.colorScheme.error) }
        }
    }
}

@Composable
private fun ChatComposer(
    value: String,
    enabled: Boolean,
    onValue: (String) -> Unit,
    onSend: () -> Unit,
) {
    Surface(tonalElevation = 4.dp, shadowElevation = 8.dp) {
        Row(
            Modifier.fillMaxWidth().navigationBarsPadding().imePadding().padding(10.dp),
            verticalAlignment = Alignment.Bottom,
        ) {
            TextField(
                value = value,
                onValueChange = onValue,
                modifier = Modifier.weight(1f),
                enabled = enabled,
                placeholder = { Text(if (enabled) "告诉 FitMind 你的计划与状态…" else "离线状态仅可查看") },
                maxLines = 5,
                shape = RoundedCornerShape(22.dp),
                colors = TextFieldDefaults.colors(
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                    disabledIndicatorColor = Color.Transparent,
                    focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                    unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                ),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { if (value.isNotBlank() && enabled) onSend() }),
            )
            Spacer(Modifier.width(8.dp))
            IconButton(
                onClick = onSend,
                enabled = enabled && value.isNotBlank(),
                modifier = Modifier.size(52.dp).clip(CircleShape)
                    .background(if (enabled && value.isNotBlank()) FitInk else MaterialTheme.colorScheme.surfaceVariant),
            ) {
                Icon(
                    Icons.AutoMirrored.Rounded.Send,
                    "发送",
                    tint = if (enabled && value.isNotBlank()) Color.White else MaterialTheme.colorScheme.outline,
                )
            }
        }
    }
}

@Composable
private fun EmptyConversation(modifier: Modifier = Modifier) {
    Column(modifier.padding(28.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            Modifier.size(72.dp).clip(CircleShape).background(
                Brush.linearGradient(listOf(FitBlue.copy(alpha = 0.18f), FitMint.copy(alpha = 0.26f))),
            ),
            contentAlignment = Alignment.Center,
        ) { Icon(Icons.Rounded.AutoAwesome, null, tint = FitBlue, modifier = Modifier.size(30.dp)) }
        Text("今天想从哪里开始？", style = MaterialTheme.typography.headlineMedium, modifier = Modifier.padding(top = 18.dp))
        Text(
            "记录训练、饮食与身体状态，或让 FitMind 给你今天的建议。",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 8.dp),
        )
    }
}
