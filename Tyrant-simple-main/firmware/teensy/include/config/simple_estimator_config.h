#pragma once

#include "estimation/simple_state_estimator.h"

namespace TyrantSimpleEstimatorConfig
{

inline TyrantSimpleEstimator::Config makeDevelopmentConfig()
{
    TyrantSimpleEstimator::Config config {};

    config.required_stationary_samples = 50;

    config.gravity_mps2 = 9.80665f;
    config.accel_norm_tolerance_mps2 = 0.75f;
    config.max_stationary_gyro_norm_rad_s = 0.10f;

    // Hardware coherent samples are near 10 Hz. Keep margin.
    config.max_dt_s = 0.20f;

    // Complementary filter time constant.
    config.roll_pitch_time_constant_s = 1.0f;

    // 2-state yaw KF: [yaw, yaw-rate bias].
    config.yaw_initial_variance_rad2 = 0.05f;
    config.yaw_rate_bias_initial_variance_rad2ps2 = 0.01f;
    config.yaw_process_noise_rad2_per_s = 1.0e-4f;
    config.yaw_rate_bias_process_noise_rad2ps3 = 1.0e-6f;
    config.yaw_measurement_variance_rad2 = 0.01f;

    config.min_abs_cos_pitch = 0.20f;

    config.heading_timeout_us = 1000000U;
    config.depth_timeout_us = 2000000U;

    // Development-only identity calibration.
    config.magnetometer_calibration.soft_iron[0][0] = 1.0f;
    config.magnetometer_calibration.soft_iron[1][1] = 1.0f;
    config.magnetometer_calibration.soft_iron[2][2] = 1.0f;

    return config;
}

} // namespace TyrantSimpleEstimatorConfig
