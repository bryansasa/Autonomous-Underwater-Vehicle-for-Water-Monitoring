#include "application/emergency_recovery_manager.h"

#include <math.h>

namespace
{
TyrantEmergency::Config runtime_config {};
bool config_valid = false;

TyrantEmergency::Policy active_policy = TyrantEmergency::Policy::NONE;
TyrantEmergency::State recovery_state = TyrantEmergency::State::INACTIVE;
TyrantEmergency::Reason recovery_reason = TyrantEmergency::Reason::NONE;
uint32_t recovery_started_ms = 0;
uint32_t command_sequence = 0;

bool validConfig(const TyrantEmergency::Config &config)
{
    return
        isfinite(config.surface_target_depth_m) &&
        config.surface_target_depth_m >= 0.0f &&
        isfinite(config.surface_tolerance_m) &&
        config.surface_tolerance_m > 0.0f &&
        isfinite(config.ascent_command) &&
        config.ascent_command > 0.0f &&
        config.ascent_command <= 1.0f &&
        config.max_runtime_ms > 0;
}

bool stateUsable(const TyrantSimpleEstimator::State &state)
{
    return
        state.attitude_valid &&
        state.depth_valid &&
        state.status != TyrantSimpleEstimator::Status::FAULT &&
        isfinite(state.roll_rad) &&
        isfinite(state.pitch_rad) &&
        isfinite(state.depth_m);
}

void neutral(TyrantControl::ManualCommand &command)
{
    command = TyrantControl::ManualCommand {};
    command.sequence = ++command_sequence;
}

uint32_t elapsedMs(uint32_t now_ms)
{
    return static_cast<uint32_t>(now_ms - recovery_started_ms);
}

} // namespace

namespace TyrantEmergency
{

void init(const Config &config)
{
    runtime_config = config;
    config_valid = validConfig(runtime_config);
    reset();
}

void reset()
{
    active_policy = Policy::NONE;
    recovery_state = State::INACTIVE;
    recovery_reason = Reason::NONE;
    recovery_started_ms = 0;
    command_sequence = 0;
}

bool trigger(
    Policy policy,
    const TyrantSimpleEstimator::State &state,
    uint32_t now_ms
)
{
    if (!config_valid || policy == Policy::NONE)
    {
        return false;
    }

    if (policy == Policy::CONTROLLED_SURFACE && !stateUsable(state))
    {
        active_policy = policy;
        recovery_state = State::FAILED;
        recovery_reason = Reason::INVALID_STATE;
        recovery_started_ms = now_ms;
        return false;
    }

    active_policy = policy;
    recovery_state = State::ACTIVE;
    recovery_reason = Reason::ACCEPTED;
    recovery_started_ms = now_ms;
    command_sequence = 0;
    return true;
}

bool update(
    const TyrantSimpleEstimator::State &state,
    uint32_t now_ms,
    TyrantControl::ManualCommand &command
)
{
    neutral(command);

    if (recovery_state != State::ACTIVE)
    {
        return false;
    }

    if (active_policy == Policy::ZERO_THRUST)
    {
        return false;
    }

    if (active_policy != Policy::CONTROLLED_SURFACE)
    {
        recovery_state = State::FAILED;
        recovery_reason = Reason::INVALID_STATE;
        return false;
    }

    if (!stateUsable(state))
    {
        recovery_state = State::FAILED;
        recovery_reason = Reason::INVALID_STATE;
        return false;
    }

    if (elapsedMs(now_ms) > runtime_config.max_runtime_ms)
    {
        recovery_state = State::FAILED;
        recovery_reason = Reason::TIMEOUT;
        return false;
    }

    if (
        state.depth_m <=
        runtime_config.surface_target_depth_m + runtime_config.surface_tolerance_m
    )
    {
        recovery_state = State::COMPLETE;
        recovery_reason = Reason::SURFACE_REACHED;
        return false;
    }

    // Positive depth is down, therefore negative heave commands ascent.
    command.heave = -runtime_config.ascent_command;
    return true;
}

Status getStatus(uint32_t now_ms)
{
    Status status {};
    status.policy = active_policy;
    status.state = recovery_state;
    status.reason = recovery_reason;
    status.elapsed_ms = recovery_state == State::INACTIVE
        ? 0
        : elapsedMs(now_ms);
    status.actuation_requested =
        recovery_state == State::ACTIVE &&
        active_policy == Policy::CONTROLLED_SURFACE;
    return status;
}

} // namespace TyrantEmergency
