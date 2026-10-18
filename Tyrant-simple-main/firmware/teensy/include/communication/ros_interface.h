#pragma once

#include <Arduino.h>

#include "application/emergency_recovery_manager.h"
#include "application/mission_manager.h"
#include "actuation/thruster_backend.h"
#include "control/control_types.h"
#include "control/thruster_allocator.h"
#include "estimation/simple_state_estimator.h"
#include "sensors/sensor_types.h"
#include "sysid/sysid_recorder.h"

namespace TyrantROS
{

struct ModeRequestData
{
    uint32_t request_id;
    uint8_t requested_mode;
};

struct DepthReferenceRequestData
{
    uint32_t request_id;
    uint8_t command;
};

struct ManualCommandData
{
    uint32_t sequence;

    float surge;
    float sway;
    float heave;

    float roll;
    float pitch;
    float yaw;
};



struct MissionCommandData
{
    uint32_t request_id;
    uint8_t command;
    uint8_t step_type;
    float target;
    float effort;
    uint32_t duration_ms;
    float tolerance;
};

struct EmergencyControlData
{
    uint32_t request_id;
    uint8_t command;
};

struct SysIdControlData
{
    uint32_t request_id;
    uint8_t command;
    uint32_t experiment_id;
    uint16_t profile_id;
};

struct ErrorStats
{
    uint32_t publish_failures;
    uint32_t executor_failures;
    uint32_t entity_create_failures;
    uint32_t entity_destroy_failures;
};

void setupTransport();
bool pingAgent(uint32_t timeout_ms, uint8_t attempts);
bool createEntities();
void destroyEntities();
void spin();

void publishHeartbeat();

void publishWrenchRequest(
    const TyrantControl::WrenchRequest &request
);

void publishThrusterCommand(
    const TyrantControl::ThrusterCommand &command,
    bool allocator_ready,
    bool mock_backend,
    uint64_t timestamp_us
);

void publishActuatorStatus(
    const TyrantActuation::ThrusterBackendStatus &status,
    uint64_t timestamp_us
);


void publishMissionStatus(
    uint32_t request_id,
    uint8_t command,
    bool accepted,
    const TyrantMission::Status &status
);

void publishEmergencyStatus(
    uint32_t request_id,
    uint8_t command,
    bool accepted,
    const TyrantEmergency::Status &status
);

void publishSysIdStatus(
    uint32_t request_id,
    uint8_t command,
    bool accepted,
    const TyrantSysId::SessionStatus &status
);

void publishSysIdSample(
    const TyrantSysId::Sample &sample
);

void publishModeStatus(
    uint32_t request_id,
    uint8_t current_mode,
    uint8_t requested_mode,
    bool request_accepted,
    uint8_t reason,
    bool communication_healthy,
    bool propulsion_allowed
);

void publishSystemHealth(
    bool communication_healthy,
    bool estimator_ready,
    bool autonomy_ready,
    bool propulsion_allowed,
    uint8_t current_mode,
    uint32_t host_heartbeat_age_ms
);

void publishSimpleState(
    const TyrantSimpleEstimator::State &state,
    uint64_t timestamp_us
);

void publishImuTelemetry(
    const TyrantSensors::ImuSample &sample,
    const TyrantSensors::SensorHealth &health,
    uint32_t bytes_received,
    uint32_t register_updates,
    uint32_t samples_produced,
    uint32_t samples_dropped,
    bool available
);

void publishPressureTelemetry(
    const TyrantSensors::PressureSample &sample,
    const TyrantSensors::SensorHealth &health,
    uint32_t read_attempts,
    uint32_t read_successes,
    uint32_t samples_produced,
    bool available
);

void publishDepthReferenceStatus(
    uint32_t request_id,
    uint8_t command,
    bool accepted,
    uint8_t reason,
    bool reference_valid,
    float surface_pressure_pa
);

void publishCommunicationDiagnostics(
    uint8_t connection_state,
    uint32_t connection_count,
    uint32_t disconnect_count,
    uint32_t reconnect_count,
    uint32_t publish_failures,
    uint32_t executor_failures,
    uint32_t entity_create_failures,
    uint32_t entity_destroy_failures
);

bool takeModeRequest(ModeRequestData &request);
bool takeDepthReferenceRequest(DepthReferenceRequestData &request);
bool takeManualCommand(ManualCommandData &command);
bool takeMissionCommand(MissionCommandData &command);
bool takeEmergencyControl(EmergencyControlData &control);
bool takeSysIdControl(SysIdControlData &control);
bool takeSimStateInput(TyrantSimpleEstimator::State &state);
bool takeHostHeartbeat();

ErrorStats getErrorStats();

#ifdef TYRANT_ENABLE_DIAGNOSTICS
void publishResponse(uint32_t value);
bool hasNewCommand();
uint32_t getLastCommand();
#endif

} // namespace TyrantROS
