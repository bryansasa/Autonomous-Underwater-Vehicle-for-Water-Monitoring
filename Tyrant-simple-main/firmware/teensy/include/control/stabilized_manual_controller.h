#pragma once

#include "control/control_types.h"
#include "estimation/simple_state_estimator.h"

namespace TyrantControl
{

// ============================================================
// STABILIZED MANUAL CONTROLLER CONFIGURATION
//
// Output remains a normalized body-FRD wrench request.
// This controller is deliberately simple and temporary:
// - surge/sway: direct normalized effort
// - heave: depth-reference rate command
// - roll/pitch: bounded angle references
// - yaw: heading-reference rate command
// ============================================================

struct StabilizedManualControllerConfig
{
    float manual_deadzone;

    float max_depth_rate_mps;
    float min_depth_reference_m;
    float max_depth_reference_m;

    float max_roll_reference_rad;
    float max_pitch_reference_rad;
    float max_yaw_rate_rad_s;

    float depth_kp;

    float roll_kp;
    float roll_kd;

    float pitch_kp;
    float pitch_kd;

    float yaw_kp;
    float yaw_kd;

    float max_control_dt_s;
};


void initStabilizedManualController(
    const StabilizedManualControllerConfig &config
);

void resetStabilizedManualController();

WrenchRequest updateStabilizedManualController(
    const ManualCommand &command,
    const TyrantSimpleEstimator::State &state,
    bool command_fresh,
    bool propulsion_allowed,
    float dt_s
);

} // namespace TyrantControl
