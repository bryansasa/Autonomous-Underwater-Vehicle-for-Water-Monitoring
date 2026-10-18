#include "application/mission_manager.h"

#include <math.h>

namespace
{
constexpr float PI_F = 3.14159265358979323846f;
constexpr float TWO_PI_F = 2.0f * PI_F;

TyrantMission::Step steps[TyrantMission::MAX_STEPS] {};
uint8_t step_count = 0;
uint8_t current_step = 0;
uint32_t step_started_ms = 0;
uint32_t command_sequence = 0;

TyrantMission::State mission_state = TyrantMission::State::EMPTY;
TyrantMission::Reason mission_reason = TyrantMission::Reason::NONE;

float clampUnit(float value)
{
    if (value > 1.0f) return 1.0f;
    if (value < -1.0f) return -1.0f;
    return value;
}

float positiveMagnitude(float value)
{
    const float magnitude = fabsf(value);
    return magnitude > 1.0f ? 1.0f : magnitude;
}

float wrapAngleRad(float angle_rad)
{
    float wrapped = fmodf(angle_rad + PI_F, TWO_PI_F);
    if (wrapped < 0.0f)
    {
        wrapped += TWO_PI_F;
    }
    return wrapped - PI_F;
}

bool finiteStep(const TyrantMission::Step &step)
{
    return
        isfinite(step.target) &&
        isfinite(step.effort) &&
        isfinite(step.tolerance);
}

bool validStep(const TyrantMission::Step &step)
{
    if (!finiteStep(step))
    {
        return false;
    }

    switch (step.type)
    {
        case TyrantMission::StepType::WAIT:
            return step.duration_ms > 0;

        case TyrantMission::StepType::SURGE_TIME:
        case TyrantMission::StepType::SWAY_TIME:
            return
                step.duration_ms > 0 &&
                fabsf(step.effort) > 0.0f &&
                fabsf(step.effort) <= 1.0f;

        case TyrantMission::StepType::DIVE_TO_DEPTH:
        case TyrantMission::StepType::SURFACE_TO_DEPTH:
            return
                step.target >= 0.0f &&
                step.tolerance > 0.0f &&
                fabsf(step.effort) > 0.0f &&
                fabsf(step.effort) <= 1.0f;

        case TyrantMission::StepType::TURN_TO_HEADING:
            return
                step.tolerance > 0.0f &&
                step.tolerance < PI_F &&
                fabsf(step.effort) > 0.0f &&
                fabsf(step.effort) <= 1.0f;

        default:
            return false;
    }
}

void neutralCommand(TyrantControl::ManualCommand &command)
{
    command = TyrantControl::ManualCommand {};
    command.sequence = ++command_sequence;
}

void completeMission()
{
    mission_state = TyrantMission::State::COMPLETE;
    mission_reason = TyrantMission::Reason::COMPLETE;
}

void advanceStep(uint32_t now_ms)
{
    ++current_step;
    step_started_ms = now_ms;

    if (current_step >= step_count)
    {
        completeMission();
    }
}

bool elapsed(uint32_t now_ms, uint32_t duration_ms)
{
    return static_cast<uint32_t>(now_ms - step_started_ms) >= duration_ms;
}

} // namespace

namespace TyrantMission
{

void init()
{
    clear();
}

void clear()
{
    for (uint8_t index = 0; index < MAX_STEPS; ++index)
    {
        steps[index] = Step {};
    }

    step_count = 0;
    current_step = 0;
    step_started_ms = 0;
    command_sequence = 0;
    mission_state = State::EMPTY;
    mission_reason = Reason::NONE;
}

bool appendStep(const Step &step)
{
    if (mission_state == State::ACTIVE)
    {
        mission_reason = Reason::INVALID_STEP;
        return false;
    }

    if (step_count >= MAX_STEPS)
    {
        mission_reason = Reason::STEP_LIST_FULL;
        return false;
    }

    if (!validStep(step))
    {
        mission_reason = Reason::INVALID_STEP;
        return false;
    }

    steps[step_count++] = step;
    current_step = 0;
    mission_state = State::READY;
    mission_reason = Reason::ACCEPTED;
    return true;
}

bool start(uint32_t now_ms)
{
    if (step_count == 0)
    {
        mission_state = State::EMPTY;
        mission_reason = Reason::NO_STEPS;
        return false;
    }

    current_step = 0;
    step_started_ms = now_ms;
    mission_state = State::ACTIVE;
    mission_reason = Reason::ACCEPTED;
    return true;
}

void stop()
{
    if (mission_state == State::ACTIVE)
    {
        mission_state = State::STOPPED;
        mission_reason = Reason::ACCEPTED;
    }
}

bool update(
    const TyrantSimpleEstimator::State &state,
    uint32_t now_ms,
    TyrantControl::ManualCommand &command
)
{
    neutralCommand(command);

    if (mission_state != State::ACTIVE)
    {
        mission_reason = mission_state == State::COMPLETE
            ? Reason::COMPLETE
            : mission_reason;
        return false;
    }

    if (current_step >= step_count)
    {
        completeMission();
        return false;
    }

    const Step &step = steps[current_step];

    switch (step.type)
    {
        case StepType::WAIT:
        {
            if (elapsed(now_ms, step.duration_ms))
            {
                advanceStep(now_ms);
            }
            break;
        }

        case StepType::SURGE_TIME:
        {
            command.surge = clampUnit(step.effort);
            if (elapsed(now_ms, step.duration_ms))
            {
                command.surge = 0.0f;
                advanceStep(now_ms);
            }
            break;
        }

        case StepType::SWAY_TIME:
        {
            command.sway = clampUnit(step.effort);
            if (elapsed(now_ms, step.duration_ms))
            {
                command.sway = 0.0f;
                advanceStep(now_ms);
            }
            break;
        }

        case StepType::DIVE_TO_DEPTH:
        case StepType::SURFACE_TO_DEPTH:
        {
            if (!state.depth_valid || !isfinite(state.depth_m))
            {
                mission_state = State::FAILED;
                mission_reason = Reason::STATE_INVALID;
                return false;
            }

            const float error_m = step.target - state.depth_m;
            if (fabsf(error_m) <= step.tolerance)
            {
                advanceStep(now_ms);
                break;
            }

            const float effort = positiveMagnitude(step.effort);
            command.heave = error_m > 0.0f ? effort : -effort;
            break;
        }

        case StepType::TURN_TO_HEADING:
        {
            if (!state.heading_valid || !isfinite(state.yaw_rad))
            {
                mission_state = State::FAILED;
                mission_reason = Reason::STATE_INVALID;
                return false;
            }

            const float error_rad = wrapAngleRad(step.target - state.yaw_rad);
            if (fabsf(error_rad) <= step.tolerance)
            {
                advanceStep(now_ms);
                break;
            }

            const float effort = positiveMagnitude(step.effort);
            command.yaw = error_rad > 0.0f ? effort : -effort;
            break;
        }

        default:
        {
            mission_state = State::FAILED;
            mission_reason = Reason::INVALID_STEP;
            return false;
        }
    }

    return mission_state == State::ACTIVE;
}

bool readyForAuto()
{
    return
        step_count > 0 &&
        mission_state != State::FAILED &&
        mission_state != State::COMPLETE;
}

Status getStatus()
{
    Status status {};
    status.state = mission_state;
    status.reason = mission_reason;
    status.step_count = step_count;
    status.current_step = current_step;
    status.active = mission_state == State::ACTIVE;

    if (step_count > 0)
    {
        const uint8_t index = current_step < step_count
            ? current_step
            : static_cast<uint8_t>(step_count - 1);
        status.current_step_type = steps[index].type;
    }

    return status;
}

} // namespace TyrantMission
