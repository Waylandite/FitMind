package com.fitmind.app.core.di

import android.content.Context
import androidx.room.Room
import com.fitmind.app.BuildConfig
import com.fitmind.app.core.database.FitMindDao
import com.fitmind.app.core.database.FitMindDatabase
import com.fitmind.app.core.network.AccessTokenAuthenticator
import com.fitmind.app.core.network.AccessTokenInterceptor
import com.fitmind.app.core.network.FitMindApi
import com.fitmind.app.core.network.KeystoreRefreshCookiePersistence
import com.fitmind.app.core.network.RefreshApi
import com.fitmind.app.core.network.RefreshCookiePersistence
import com.fitmind.app.core.network.SecureRefreshCookieJar
import com.fitmind.app.core.network.NetworkMonitor
import com.fitmind.app.core.network.NetworkStatusProvider
import com.fitmind.app.data.AuthRepository
import com.fitmind.app.data.AuthRepositoryContract
import com.fitmind.app.data.ChatRepository
import com.fitmind.app.data.ChatRepositoryContract
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Named
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit

@Module
@InstallIn(SingletonComponent::class)
abstract class PersistenceBindings {
    @Binds
    abstract fun bindCookiePersistence(
        implementation: KeystoreRefreshCookiePersistence,
    ): RefreshCookiePersistence

    @Binds
    abstract fun bindAuthRepository(implementation: AuthRepository): AuthRepositoryContract

    @Binds
    abstract fun bindChatRepository(implementation: ChatRepository): ChatRepositoryContract

    @Binds
    abstract fun bindNetworkMonitor(implementation: NetworkMonitor): NetworkStatusProvider
}

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides
    @Named("apiBaseUrl")
    fun apiBaseUrl(): String = BuildConfig.API_BASE_URL

    @Provides
    @Singleton
    fun json(): Json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
        encodeDefaults = true
    }

    @Provides
    @Singleton
    fun database(@ApplicationContext context: Context): FitMindDatabase =
        Room.databaseBuilder(context, FitMindDatabase::class.java, "fitmind_cache.db").build()

    @Provides
    fun dao(database: FitMindDatabase): FitMindDao = database.dao()

    @Provides
    @Singleton
    fun loggingInterceptor(): HttpLoggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BASIC else HttpLoggingInterceptor.Level.NONE
        redactHeader("Authorization")
        redactHeader("Cookie")
        redactHeader("Set-Cookie")
    }

    @Provides
    @Singleton
    @Named("refresh")
    fun refreshClient(
        cookieJar: SecureRefreshCookieJar,
        logging: HttpLoggingInterceptor,
    ): OkHttpClient = OkHttpClient.Builder()
        .cookieJar(cookieJar)
        .addInterceptor(logging)
        .build()

    @Provides
    @Singleton
    fun refreshApi(
        @Named("refresh") client: OkHttpClient,
        json: Json,
    ): RefreshApi = retrofit(client, json).create(RefreshApi::class.java)

    @Provides
    @Singleton
    fun authenticatedClient(
        cookieJar: SecureRefreshCookieJar,
        tokenInterceptor: AccessTokenInterceptor,
        authenticator: AccessTokenAuthenticator,
        logging: HttpLoggingInterceptor,
    ): OkHttpClient = OkHttpClient.Builder()
        .cookieJar(cookieJar)
        .addInterceptor(tokenInterceptor)
        .addInterceptor(logging)
        .authenticator(authenticator)
        .build()

    @Provides
    @Singleton
    fun api(client: OkHttpClient, json: Json): FitMindApi =
        retrofit(client, json).create(FitMindApi::class.java)

    private fun retrofit(client: OkHttpClient, json: Json): Retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(client)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()
}
