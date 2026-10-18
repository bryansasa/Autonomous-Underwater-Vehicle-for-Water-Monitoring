#pragma once

#include <Arduino.h>

#include "control/control_types.h"
#include "estimation/simple_state_estimator.h"

namespace TyrantEmergency
{
enum class Policy : uint8_t
{
    NONE = 0,
    ZERO_THRUST = 1,
    CONTROLLED_SURFACE = 2
};

enum class State : uint8_t
{
    INACTIVE = 0,
    ACTIVE = 1,
    COMPLETE = 2,
    FAILED = 3
};

enum class Reason : uint8_t
{
    NONE = 0,
    ACCEPTED = 1,
    INVALID_STATE = 2,
    TIMEOUT = 3,
    SURFACE_REACHED = 4
};

struct Config
{
    float surface_target_depth_m;
    float surface_tolerance_m;
    float ascent_command;
    uint32_t max_runtime_ms;
};

struct Status
{
    Policy policy = Policy::NONE;
    State state = State::INACTIVE;
    Reason reason = Reason::NONE;
    uint32_t elapsed_ms = 0;
    bool actuation_requested = false;
};

void init(const Config &config);
void reset();

bool trigger(
    Policy policy,
    const TyrantSimpleEstimator::State &state,
    uint32_t now_ms
);

bool update(
    const TyrantSimpleEstimator::State &state,
    uint32_t now_ms,
    TyrantControl::ManualCommand &command
);

Status getStatus(uint32_t now_ms);

} // namespace TyrantEmergency
