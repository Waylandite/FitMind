package com.fitmind.app.core.network

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.core.content.edit
import dagger.hilt.android.qualifiers.ApplicationContext
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.inject.Inject
import javax.inject.Singleton
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl

interface RefreshCookiePersistence {
    fun read(): String?
    fun write(value: String)
    fun clear()
}

@Singleton
class KeystoreRefreshCookiePersistence @Inject constructor(
    @ApplicationContext context: Context,
) : RefreshCookiePersistence {
    private val preferences = context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    override fun read(): String? = preferences.getString(COOKIE, null)?.let(::decrypt)

    override fun write(value: String) {
        preferences.edit { putString(COOKIE, encrypt(value)) }
    }

    override fun clear() {
        preferences.edit { remove(COOKIE) }
    }

    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
        val encrypted = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        return Base64.encodeToString(cipher.iv + encrypted, Base64.NO_WRAP)
    }

    private fun decrypt(value: String): String? = runCatching {
        val payload = Base64.decode(value, Base64.NO_WRAP)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            getOrCreateKey(),
            GCMParameterSpec(GCM_TAG_LENGTH, payload.copyOfRange(0, IV_LENGTH)),
        )
        cipher.doFinal(payload.copyOfRange(IV_LENGTH, payload.size)).toString(Charsets.UTF_8)
    }.getOrNull()

    private fun getOrCreateKey(): SecretKey {
        val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE).run {
            init(
                KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                ).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256)
                    .build(),
            )
            generateKey()
        }
    }

    private companion object {
        const val PREFERENCES = "fitmind_auth"
        const val COOKIE = "refresh_cookie"
        const val KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "fitmind_refresh_cookie_key"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val IV_LENGTH = 12
        const val GCM_TAG_LENGTH = 128
    }
}

@Singleton
class SecureRefreshCookieJar @Inject constructor(
    private val persistence: RefreshCookiePersistence,
) : CookieJar {
    @Volatile
    private var refreshCookie: StoredCookie? = persistence.read()?.let(StoredCookie::decode)

    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val cookie = cookies.lastOrNull { it.name == REFRESH_COOKIE } ?: return
        if (cookie.expiresAt <= System.currentTimeMillis()) {
            clear()
            return
        }
        StoredCookie(url.scheme, url.host, url.port, cookie.toString()).also {
            refreshCookie = it
            persistence.write(it.encode())
        }
    }

    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        val stored = refreshCookie ?: return emptyList()
        val origin = HttpUrl.Builder()
            .scheme(stored.scheme)
            .host(stored.host)
            .port(stored.port)
            .build()
        val cookie = Cookie.parse(origin, stored.rawCookie) ?: run {
            clear()
            return emptyList()
        }
        if (cookie.expiresAt <= System.currentTimeMillis() || !cookie.matches(url)) {
            if (cookie.expiresAt <= System.currentTimeMillis()) clear()
            return emptyList()
        }
        return listOf(cookie)
    }

    fun clear() {
        refreshCookie = null
        persistence.clear()
    }

    private data class StoredCookie(
        val scheme: String,
        val host: String,
        val port: Int,
        val rawCookie: String,
    ) {
        fun encode() = listOf(scheme, host, port.toString(), rawCookie)
            .joinToString(SEPARATOR) { Base64.encodeToString(it.toByteArray(), Base64.NO_WRAP) }

        companion object {
            fun decode(value: String): StoredCookie? = runCatching {
                val fields = value.split(SEPARATOR).map {
                    Base64.decode(it, Base64.NO_WRAP).toString(Charsets.UTF_8)
                }
                StoredCookie(fields[0], fields[1], fields[2].toInt(), fields[3])
            }.getOrNull()
        }
    }

    private companion object {
        const val REFRESH_COOKIE = "fitmind_refresh_token"
        const val SEPARATOR = "."
    }
}
