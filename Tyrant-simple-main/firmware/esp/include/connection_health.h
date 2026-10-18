#pragma once
#include <Arduino.h>
#include <tyrant_payload_interfaces/msg/payload_communication_diagnostics.h>
class ConnectionHealthManager {
public:
    void onHostHeartbeatRx();
    void onConnected();
    void onDisconnected();
    bool isHostHealthy();
    bool isAgentConnected() const { return agent_connected_; }
    void populateDiagnostics(tyrant_payload_interfaces__msg__PayloadCommunicationDiagnostics &msg);
    uint32_t ping_failures = 0, publish_failures = 0, executor_failures = 0;
    uint32_t entity_create_failures = 0, entity_destroy_failures = 0;
private:
    bool agent_connected_ = false, host_seen_ = false, host_healthy_ = false;
    uint32_t last_rx_ms_ = 0, timeout_count_ = 0;
    uint32_t conn_count_ = 0, disconn_count_ = 0;
};
