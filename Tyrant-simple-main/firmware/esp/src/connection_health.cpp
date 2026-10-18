#include "connection_health.h"
#include "payload_config.h"
void ConnectionHealthManager::onHostHeartbeatRx() {
    // Account for a timeout even if the next packet arrives before a diagnostic tick.
    isHostHealthy();
    if (!agent_connected_) return;
    last_rx_ms_ = millis(); host_seen_ = true; host_healthy_ = true;
}
void ConnectionHealthManager::onConnected() {
    agent_connected_ = true; ++conn_count_;
    host_seen_ = false; host_healthy_ = false;
}
void ConnectionHealthManager::onDisconnected() {
    if (agent_connected_) ++disconn_count_;
    agent_connected_ = false; host_seen_ = false; host_healthy_ = false;
}
bool ConnectionHealthManager::isHostHealthy() {
    bool healthy = agent_connected_ && host_seen_ &&
        static_cast<uint32_t>(millis() - last_rx_ms_) <= PayloadConfig::HEARTBEAT_TIMEOUT_MS;
    if (host_healthy_ && !healthy) ++timeout_count_;
    host_healthy_ = healthy;
    return healthy;
}
void ConnectionHealthManager::populateDiagnostics(tyrant_payload_interfaces__msg__PayloadCommunicationDiagnostics &m) {
    m.connection_state = agent_connected_ ? 2 : (conn_count_ ? 3 : 0);
    m.agent_connected = agent_connected_;
    m.host_heartbeat_healthy = isHostHealthy();
    m.host_heartbeat_age_ms = host_seen_ ? static_cast<uint32_t>(millis()-last_rx_ms_) : UINT32_MAX;
    m.connection_count = conn_count_; m.disconnect_count = disconn_count_;
    m.reconnect_count = conn_count_ ? conn_count_-1 : 0;
    m.host_heartbeat_timeout_count = timeout_count_;
    m.ping_failures = ping_failures; m.publish_failures = publish_failures;
    m.executor_failures = executor_failures;
    m.entity_create_failures = entity_create_failures;
    m.entity_destroy_failures = entity_destroy_failures;
}
