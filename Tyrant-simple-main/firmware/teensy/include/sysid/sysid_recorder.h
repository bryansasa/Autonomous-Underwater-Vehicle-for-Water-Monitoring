#pragma once

#include <stdint.h>

#include "control/control_types.h"
#include "control/thruster_allocator.h"
#include "estimation/simple_state_estimator.h"
#include "sensors/sensor_types.h"

namespace TyrantSysId
{

constexpr uint8_t SYSID_THRUSTER_COUNT = 8;

struct SessionStatus
{
    bool active;
    uint32_t experiment_id;
    uint16_t profile_id;
    uint32_t sample_sequence;
};

struct Sample
{
    uint64_t timestamp_us;
    uint32_t experiment_id;
    uint16_t profile_id;
    uint32_t sample_sequence;

    uint8_t mode;
    bool propulsion_allowed;
    bool command_fresh;

    TyrantControl::ManualCommand manual_command;
    TyrantControl::WrenchRequest requested_wrench;

    bool thruster_command_valid;
    float thruster_command[SYSID_THRUSTER_COUNT];

    TyrantSimpleEstimator::State state;

    TyrantSensors::ImuSample imu;
    bool imu_valid;

    TyrantSensors::PressureSample pressure;
    bool pressure_valid;
};

void init();

void startSession(
    uint32_t experiment_id,
    uint16_t profile_id
);

void stopSession();

SessionStatus getStatus();

bool sampleDue(uint32_t now_us);

bool makeSample(
    uint64_t timestamp_us,
    uint8_t mode,
    bool propulsion_allowed,
    const TyrantControl::ManualCommand &manual_command,
    bool command_fresh,
    const TyrantControl::WrenchRequest &requested_wrench,
    const TyrantControl::ThrusterCommand &thruster_command,
    const TyrantSimpleEstimator::State &state,
    const TyrantSensors::ImuSample &imu,
    bool imu_valid,
    const TyrantSensors::PressureSample &pressure,
    bool pressure_valid,
    Sample &sample
);

} // namespace TyrantSysId
