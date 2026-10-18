#include "control/stabilized_manual_controller.h"
#include "control/manual_wrench_mapper.h"

#include <math.h>

namespace
{
constexpr float PI_F = 3.14159265358979323846f;
constexpr float TWO_PI_F = 2.0f * PI_F;

TyrantControl::StabilizedManualControllerConfig runtime_config {};
bool config_valid = false;

float depth_reference_m = 0.0f;
bool depth_reference_valid = false;

float yaw_reference_rad = 0.0f;
bool yaw_reference_valid = false;


// ============================================================
// HELPERS
// ============================================================

bool finitePositive(float value)
{
    return isfinite(value) && value > 0.0f;
}


bool finiteNonNegative(float value)
{
    return isfinite(value) && value >= 0.0f;
}


float clampValue(
    float value,
    float minimum,
    float maximum
)
{
    if (value < minimum)
    {
        return minimum;
    }

    if (value > maximum)
    {
        return maximum;
    }

    return value;
}


float clampNormalized(float value)
{
    return clampValue(value, -1.0f, 1.0f);
}


float applyDeadzone(float value)
{
    if (fabsf(value) <= runtime_config.manual_deadzone)
    {
        return 0.0f;
    }

    return value;
}


float wrapAngleRad(float angle_rad)
{
    if (!isfinite(angle_rad))
    {
        return NAN;
    }

    float wrapped = fmodf(angle_rad + PI_F, TWO_PI_F);

    if (wrapped < 0.0f)
    {
        wrapped += TWO_PI_F;
    }

    return wrapped - PI_F;
}


bool configValid(
    const TyrantControl::StabilizedManualControllerConfig &config
)
{
    return
        finiteNonNegative(config.manual_deadzone) &&
        config.manual_deadzone < 1.0f &&
        finitePositive(config.max_depth_rate_mps) &&
        isfinite(config.min_depth_reference_m) &&
        isfinite(config.max_depth_reference_m) &&
        config.max_depth_reference_m > config.min_depth_reference_m &&
        finitePositive(config.max_roll_reference_rad) &&
        finitePositive(config.max_pitch_reference_rad) &&
        finitePositive(config.max_yaw_rate_rad_s) &&
        finiteNonNegative(config.depth_kp) &&
        finiteNonNegative(config.roll_kp) &&
        finiteNonNegative(config.roll_kd) &&
        finiteNonNegative(config.pitch_kp) &&
        finiteNonNegative(config.pitch_kd) &&
        finiteNonNegative(config.yaw_kp) &&
        finiteNonNegative(config.yaw_kd) &&
        finitePositive(config.max_control_dt_s);
}


bool attitudeStateFinite(
    const TyrantSimpleEstimator::State &state
)
{
    return
        isfinite(state.roll_rad) &&
        isfinite(state.pitch_rad) &&
        isfinite(state.yaw_rad) &&
        isfinite(state.angular_velocity_b_rad_s.x) &&
        isfinite(state.angular_velocity_b_rad_s.y) &&
        isfinite(state.angular_velocity_b_rad_s.z);
}

} // namespace


namespace TyrantControl
{

void resetStabilizedManualController()
{
    depth_reference_m = 0.0f;
    depth_reference_valid = false;

    yaw_reference_rad = 0.0f;
    yaw_reference_valid = false;
}


void initStabilizedManualController(
    const StabilizedManualControllerConfig &config
)
{
    runtime_config = config;
    config_valid = configValid(runtime_config);

    resetStabilizedManualController();
}


WrenchRequest updateStabilizedManualController(
    const ManualCommand &command,
    const TyrantSimpleEstimator::State &state,
    bool command_fresh,
    bool propulsion_allowed,
    float dt_s
)
{
    if (
        !config_valid ||
        !command_fresh ||
        !propulsion_allowed ||
        !isfinite(dt_s) ||
        dt_s <= 0.0f ||
        dt_s > runtime_config.max_control_dt_s ||
        !state.attitude_valid ||
        state.status == TyrantSimpleEstimator::Status::FAULT ||
        !attitudeStateFinite(state)
    )
    {
        resetStabilizedManualController();

        return makeZeroWrenchRequest(
            command.sequence,
            command_fresh
        );
    }

    WrenchRequest request {};

    request.source_sequence = command.sequence;
    request.command_fresh = true;
    request.enabled = true;


    // ============================================================
    // SURGE / SWAY
    // Direct manual normalized wrench. No velocity estimator exists.
    // ============================================================

    request.x = clampNormalized(
        applyDeadzone(command.surge)
    );

    request.y = clampNormalized(
        applyDeadzone(command.sway)
    );


    // ============================================================
    // DEPTH HOLD
    // Positive depth and positive body Z are both down.
    // ============================================================

    if (state.depth_valid && isfinite(state.depth_m))
    {
        if (!depth_reference_valid)
        {
            depth_reference_m = state.depth_m;
            depth_reference_valid = true;
        }

        const float heave_command = applyDeadzone(command.heave);

        depth_reference_m +=
            heave_command *
            runtime_config.max_depth_rate_mps *
            dt_s;

        depth_reference_m = clampValue(
            depth_reference_m,
            runtime_config.min_depth_reference_m,
            runtime_config.max_depth_reference_m
        );

        const float depth_error_m =
            depth_reference_m - state.depth_m;

        request.z = clampNormalized(
            runtime_config.depth_kp * depth_error_m
        );
    }
    else
    {
        depth_reference_valid = false;
        request.z = 0.0f;
    }


    // ============================================================
    // ROLL / PITCH STABILIZATION
    // Sticks command bounded attitude angles.
    // ============================================================

    const float roll_reference_rad =
        applyDeadzone(command.roll) *
        runtime_config.max_roll_reference_rad;

    const float pitch_reference_rad =
        applyDeadzone(command.pitch) *
        runtime_config.max_pitch_reference_rad;

    const float roll_error_rad =
        wrapAngleRad(roll_reference_rad - state.roll_rad);

    const float pitch_error_rad =
        pitch_reference_rad - state.pitch_rad;

    request.k = clampNormalized(
        runtime_config.roll_kp * roll_error_rad -
        runtime_config.roll_kd * state.angular_velocity_b_rad_s.x
    );

    request.m = clampNormalized(
        runtime_config.pitch_kp * pitch_error_rad -
        runtime_config.pitch_kd * state.angular_velocity_b_rad_s.y
    );


    // ============================================================
    // HEADING HOLD
    // Yaw stick slews the heading reference. Releasing the stick
    // holds the latest heading. Positive yaw is clockwise in NED.
    // ============================================================

    if (state.heading_valid)
    {
        if (!yaw_reference_valid)
        {
            yaw_reference_rad = state.yaw_rad;
            yaw_reference_valid = true;
        }

        const float yaw_command = applyDeadzone(command.yaw);

        yaw_reference_rad = wrapAngleRad(
            yaw_reference_rad +
            yaw_command * runtime_config.max_yaw_rate_rad_s * dt_s
        );

        const float yaw_error_rad = wrapAngleRad(
            yaw_reference_rad - state.yaw_rad
        );

        request.n = clampNormalized(
            runtime_config.yaw_kp * yaw_error_rad -
            runtime_config.yaw_kd * state.angular_velocity_b_rad_s.z
        );
    }
    else
    {
        yaw_reference_valid = false;
        request.n = 0.0f;
    }

    return request;
}

} // namespace TyrantControl
