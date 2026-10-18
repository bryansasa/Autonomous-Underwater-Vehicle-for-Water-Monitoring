#include "sysid/sysid_recorder.h"

namespace
{
constexpr uint32_t SYSID_SAMPLE_PERIOD_US = 50000U; // 20 Hz

bool active = false;
uint32_t experiment_id = 0;
uint16_t profile_id = 0;
uint32_t sample_sequence = 0;
uint32_t last_sample_us = 0;

} // namespace

namespace TyrantSysId
{

void init()
{
    active = false;
    experiment_id = 0;
    profile_id = 0;
    sample_sequence = 0;
    last_sample_us = 0;
}

void startSession(
    uint32_t new_experiment_id,
    uint16_t new_profile_id
)
{
    active = true;
    experiment_id = new_experiment_id;
    profile_id = new_profile_id;
    sample_sequence = 0;
    last_sample_us = 0;
}

void stopSession()
{
    active = false;
    last_sample_us = 0;
}

SessionStatus getStatus()
{
    return {
        active,
        experiment_id,
        profile_id,
        sample_sequence
    };
}

bool sampleDue(uint32_t now_us)
{
    if (!active)
    {
        return false;
    }

    if (
        last_sample_us != 0 &&
        static_cast<uint32_t>(now_us - last_sample_us) < SYSID_SAMPLE_PERIOD_US
    )
    {
        return false;
    }

    last_sample_us = now_us;
    return true;
}

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
)
{
    if (!active)
    {
        return false;
    }

    sample = Sample {};

    sample.timestamp_us = timestamp_us;
    sample.experiment_id = experiment_id;
    sample.profile_id = profile_id;
    sample.sample_sequence = ++sample_sequence;

    sample.mode = mode;
    sample.propulsion_allowed = propulsion_allowed;
    sample.command_fresh = command_fresh;

    sample.manual_command = manual_command;
    sample.requested_wrench = requested_wrench;

    // ============================================================
    // ACTUATOR-SIDE INPUT
    // This is the exact command accepted by the current backend.
    // With the mock backend it is suitable for software regression;
    // after PWM integration the same fields become the plant input.
    // ============================================================

    sample.thruster_command_valid = thruster_command.valid;

    for (uint8_t index = 0; index < SYSID_THRUSTER_COUNT; ++index)
    {
        sample.thruster_command[index] = thruster_command.value[index];
    }

    sample.state = state;
    sample.imu = imu;
    sample.imu_valid = imu_valid;
    sample.pressure = pressure;
    sample.pressure_valid = pressure_valid;

    return true;
}

} // namespace TyrantSysId
