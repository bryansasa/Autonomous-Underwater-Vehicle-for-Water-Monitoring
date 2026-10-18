#pragma once

#include <Arduino.h>

#include "control/control_types.h"
#include "estimation/simple_state_estimator.h"

namespace TyrantMission
{
constexpr uint8_t MAX_STEPS = 16;

enum class StepType : uint8_t
{
    WAIT = 1,
    SURGE_TIME = 2,
    SWAY_TIME = 3,
    DIVE_TO_DEPTH = 4,
    TURN_TO_HEADING = 5,
    SURFACE_TO_DEPTH = 6
};

enum class State : uint8_t
{
    EMPTY = 0,
    READY = 1,
    ACTIVE = 2,
    COMPLETE = 3,
    STOPPED = 4,
    FAILED = 5
};

enum class Reason : uint8_t
{
    NONE = 0,
    ACCEPTED = 1,
    NO_STEPS = 2,
    STEP_LIST_FULL = 3,
    INVALID_STEP = 4,
    STATE_INVALID = 5,
    NOT_ACTIVE = 6,
    COMPLETE = 7
};

struct Step
{
    StepType type = StepType::WAIT;
    float target = 0.0f;
    float effort = 0.0f;
    uint32_t duration_ms = 0;
    float tolerance = 0.0f;
};

struct Status
{
    State state = State::EMPTY;
    Reason reason = Reason::NONE;
    uint8_t step_count = 0;
    uint8_t current_step = 0;
    StepType current_step_type = StepType::WAIT;
    bool active = false;
};

void init();
void clear();

bool appendStep(const Step &step);
bool start(uint32_t now_ms);
void stop();

bool update(
    const TyrantSimpleEstimator::State &state,
    uint32_t now_ms,
    TyrantControl::ManualCommand &command
);

bool readyForAuto();
Status getStatus();

} // namespace TyrantMission
