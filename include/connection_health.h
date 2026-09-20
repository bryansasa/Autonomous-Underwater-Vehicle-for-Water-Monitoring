#ifndef CONNECTION_HEALTH_H
#define CONNECTION_HEALTH_H

#include <Arduino.h>
#include <tyrant_payload_interfaces/msg/payload_communication_diagnostics.h>

class ConnectionHealthManager {
public:
    ConnectionHealthManager();

    // Event hooks
    void onHostHeartbeatRx();
    void onConnected();
    void onDisconnected();

    // Getter status
    bool isHostHealthy() const;
    bool isAgentConnected() const;

    // Pengisi struct diagnostics untuk dipublish ke ROS
    void populateDiagnostics(tyrant_payload_interfaces__msg__PayloadCommunicationDiagnostics &msg);

private:
    bool agent_connected;
    bool host_seen;
    bool host_healthy;
    uint32_t last_rx_ms;
    uint32_t timeout_count;

    uint32_t conn_count;
    uint32_t disconn_count;
    uint32_t reconn_count;

    const uint32_t timeout_limit_ms;
};

#endif