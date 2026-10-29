package com.fitmind.app.core.network

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.distinctUntilChanged

@Singleton
class NetworkMonitor @Inject constructor(
    @ApplicationContext context: Context,
) : NetworkStatusProvider {
    private val manager = context.getSystemService(ConnectivityManager::class.java)

    override val isOnline: Flow<Boolean> = callbackFlow {
        fun current(): Boolean = manager.activeNetwork
            ?.let(manager::getNetworkCapabilities)
            ?.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED) == true

        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) { trySend(current()) }
            override fun onLost(network: Network) { trySend(current()) }
            override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) {
                trySend(capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED))
            }
        }
        trySend(current())
        manager.registerDefaultNetworkCallback(callback)
        awaitClose { manager.unregisterNetworkCallback(callback) }
    }.distinctUntilChanged()
}

interface NetworkStatusProvider {
    val isOnline: Flow<Boolean>
}
