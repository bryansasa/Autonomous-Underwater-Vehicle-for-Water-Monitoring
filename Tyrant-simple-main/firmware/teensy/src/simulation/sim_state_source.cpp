#include "simulation/sim_state_source.h"

#include <math.h>

namespace
{
TyrantSimulation::SimStateSourceConfig runtime_config {};
TyrantSimpleEstimator::State latest_state {};
uint32_t last_receive_us = 0;
bool state_seen = false;

bool stateFinite(const TyrantSimpleEstimator::State &state)
{
    return
        isfinite(state.roll_rad) &&
        isfinite(state.pitch_rad) &&
        isfinite(state.yaw_rad) &&
        isfinite(state.angular_velocity_b_rad_s.x) &&
        isfinite(state.angular_velocity_b_rad_s.y) &&
        isfinite(state.angular_velocity_b_rad_s.z) &&
        isfinite(state.yaw_rate_bias_rad_s) &&
        isfinite(state.depth_m);
}

void invalidateState(TyrantSimpleEstimator::State &state)
{
    state = TyrantSimpleEstimator::State {};
    state.status = TyrantSimpleEstimator::Status::DEGRADED;
    state.attitude_valid = false;
    state.heading_valid = false;
    state.depth_valid = false;
}
}

namespace TyrantSimulation
{

void initSimStateSource(const SimStateSourceConfig &config)
{
    runtime_config = config;
    state_seen = false;
    last_receive_us = 0;
    invalidateState(latest_state);
}

bool acceptSimState(
    const TyrantSimpleEstimator::State &state,
    uint32_t received_at_us)
{
    if (
        runtime_config.timeout_us == 0 ||
        !stateFinite(state) ||
        state.status == TyrantSimpleEstimator::Status::FAULT)
    {
        return false;
    }

    latest_state = state;
    last_receive_us = received_at_us;
    state_seen = true;
    return true;
}

bool getSimState(
    TyrantSimpleEstimator::State &state,
    uint32_t now_us)
{
    if (!state_seen || runtime_config.timeout_us == 0)
    {
        invalidateState(state);
        return false;
    }

    const uint32_t age_us =
        static_cast<uint32_t>(now_us - last_receive_us);

    if (age_us > runtime_config.timeout_us)
    {
        state = latest_state;
        state.status = TyrantSimpleEstimator::Status::DEGRADED;
        state.attitude_valid = false;
        state.heading_valid = false;
        state.depth_valid = false;
        return false;
    }

    state = latest_state;

    return
        state.attitude_valid &&
        state.heading_valid &&
        state.depth_valid &&
        state.status != TyrantSimpleEstimator::Status::FAULT;
}

uint32_t simStateAgeUs(uint32_t now_us)
{
    if (!state_seen)
    {
        return UINT32_MAX;
    }

    return static_cast<uint32_t>(now_us - last_receive_us);
}

bool simStateSeen()
{
    return state_seen;
}

} // namespace TyrantSimulation
