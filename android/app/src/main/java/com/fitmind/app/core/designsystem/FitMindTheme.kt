package com.fitmind.app.core.designsystem

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

val FitBlue = Color(0xFF5F89FF)
val FitMint = Color(0xFF74CEB5)
val FitInk = Color(0xFF132331)
val FitMist = Color(0xFFF4F7F6)
val FitSurface = Color(0xFFFBFCFB)

private val LightColors = lightColorScheme(
    primary = Color(0xFF3D65D8),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDCE4FF),
    onPrimaryContainer = FitInk,
    secondary = Color(0xFF347F6D),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFC3F1E2),
    background = FitMist,
    onBackground = FitInk,
    surface = FitSurface,
    onSurface = FitInk,
    surfaceVariant = Color(0xFFE8EEEC),
    outline = Color(0xFF71807E),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFAFC6FF),
    onPrimary = Color(0xFF092F79),
    primaryContainer = Color(0xFF264B9D),
    secondary = Color(0xFF8DDBC5),
    onSecondary = Color(0xFF00382D),
    secondaryContainer = Color(0xFF1B5B4C),
    background = Color(0xFF0B1518),
    onBackground = Color(0xFFE4ECEA),
    surface = Color(0xFF111D21),
    onSurface = Color(0xFFE4ECEA),
    surfaceVariant = Color(0xFF263437),
    outline = Color(0xFF899997),
)

@Composable
fun FitMindTheme(content: @Composable () -> Unit) {
    val darkTheme = isSystemInDarkTheme()
    val context = LocalContext.current
    val colors = if (darkTheme) DarkColors else LightColors
    MaterialTheme(
        colorScheme = colors,
        typography = FitMindTypography,
        shapes = FitMindShapes,
        content = content,
    )
}
