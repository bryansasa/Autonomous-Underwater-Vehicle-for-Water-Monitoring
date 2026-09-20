#include "connection_health.h"

ConnectionHealthManager::ConnectionHealthManager()
    : agent_connected(false),
      host_seen(false),
      host_healthy(false),
      last_rx_ms(0),
      timeout_count(0),
      conn_count(0),
      disconn_count(0),
      reconn_count(0),
      timeout_limit_ms(1000) {}

void ConnectionHealthManager::onHostHeartbeatRx() {
    last_rx_ms = millis();
    host_seen = true;
}

void ConnectionHealthManager::onConnected() {
    agent_connected = true;
    conn_count++;
    if (conn_count > 1) {
        reconn_count++;
    }
}

void ConnectionHealthManager::onDisconnected() {
    agent_connected = false;
    disconn_count++;
    // Invalidate state host saat koneksi putus (Addendum A Section 4.4)
    host_seen = false;
    host_healthy = false;
}

bool ConnectionHealthManager::isHostHealthy() const {
    return host_healthy;
}

bool ConnectionHealthManager::isAgentConnected() const {
    return agent_connected;
}

void ConnectionHealthManager::populateDiagnostics(tyrant_payload_interfaces__msg__PayloadCommunicationDiagnostics &msg) {
    uint32_t now = millis();
    uint32_t age_ms = 0xFFFFFFFF; // Nilai sentinel jika belum pernah terima paket

    if (host_seen) {
        age_ms = now - last_rx_ms;
        if (age_ms <= timeout_limit_ms) {
            host_healthy = true;
        } else {
            if (host_healthy) {
                // Transisi dari sehat -> timeout (dihitung tepat 1 kali per siklus timeout)
                timeout_count++;
            }
            host_healthy = false;
        }
    } else {
        host_healthy = false;
    }

    // Field message sesuai schema Addendum A Section 6
    msg.connection_state = agent_connected ? 2 : 3; // 2=CONNECTED, 3=DISCONNECTED
    msg.agent_connected = agent_connected;
    msg.host_heartbeat_healthy = host_healthy;
    msg.host_heartbeat_age_ms = age_ms;
    msg.connection_count = conn_count;
    msg.disconnect_count = disconn_count;
    msg.reconnect_count = reconn_count;
    msg.host_heartbeat_timeout_count = timeout_count;
    msg.ping_failures = 0;
    msg.publish_failures = 0;
    msg.executor_failures = 0;
    msg.entity_create_failures = 0;
    msg.entity_destroy_failures = 0;
}