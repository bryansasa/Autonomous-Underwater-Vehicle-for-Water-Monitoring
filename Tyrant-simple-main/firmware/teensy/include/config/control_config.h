#pragma once

#include <Arduino.h>

#include "control/stabilized_manual_controller.h"

namespace TyrantControlConfig
{
    // Manual command must be refreshed continuously by the host.
    constexpr uint32_t MANUAL_COMMAND_TIMEOUT_MS = 250;


    // ============================================================
    // STABILIZED MANUAL DEVELOPMENT CONFIG
    //
    // These are provisional normalized-wrench gains for dry/bench
    // validation. Wet tuning must be done after TAM/thrusters exist.
    // ============================================================

    inline TyrantControl::StabilizedManualControllerConfig
    makeDevelopmentStabilizedManualConfig()
    {
        TyrantControl::StabilizedManualControllerConfig config {};

        config.manual_deadzone = 0.05f;

        // Positive heave command means increasing positive-down depth.
        config.max_depth_rate_mps = 0.25f;
        config.min_depth_reference_m = 0.0f;
        config.max_depth_reference_m = 10.0f;

        // Roll/pitch sticks request bounded attitude angles.
        config.max_roll_reference_rad = 0.2617994f;   // 15 deg
        config.max_pitch_reference_rad = 0.2617994f;  // 15 deg

        // Yaw stick slews the held heading reference.
        config.max_yaw_rate_rad_s = 0.7853982f;       // 45 deg/s

        // Normalized wrench gains. No integral term yet.
        config.depth_kp = 0.80f;

        config.roll_kp = 2.00f;
        config.roll_kd = 0.35f;

        config.pitch_kp = 2.00f;
        config.pitch_kd = 0.35f;

        config.yaw_kp = 1.50f;
        config.yaw_kd = 0.25f;

        // A long control gap invalidates reference integration.
        config.max_control_dt_s = 0.10f;

        return config;
    }
}
