#pragma once

#include <stdint.h>

#include "sensors/sensor_types.h"

namespace TyrantSimpleEstimator
{

// ============================================================
// SIMPLE ESTIMATOR STATUS
// ============================================================

enum class Status : uint8_t
{
    INITIALIZING = 0,
    RUNNING = 1,
    DEGRADED = 2,
    FAULT = 3
};


// ============================================================
// SMALL MATH / CALIBRATION TYPES
// ============================================================

struct Vector3
{
    float x;
    float y;
    float z;
};

struct MagnetometerCalibration
{
    Vector3 hard_iron_offset_lsb;
    float soft_iron[3][3];
};


// ============================================================
// CONFIGURATION
//
// No position, linear velocity, accelerometer bias, quaternion
// state, or 15x15 covariance exists in this estimator.
// ============================================================

struct Config
{
    uint32_t required_stationary_samples;

    float gravity_mps2;
    float accel_norm_tolerance_mps2;
    float max_stationary_gyro_norm_rad_s;

    float max_dt_s;
    float roll_pitch_time_constant_s;

    float yaw_initial_variance_rad2;
    float yaw_rate_bias_initial_variance_rad2ps2;
    float yaw_process_noise_rad2_per_s;
    float yaw_rate_bias_process_noise_rad2ps3;
    float yaw_measurement_variance_rad2;

    float min_abs_cos_pitch;

    uint32_t heading_timeout_us;
    uint32_t depth_timeout_us;

    MagnetometerCalibration magnetometer_calibration;
};


// ============================================================
// PUBLISHED REDUCED STATE
// ============================================================

struct State
{
    float roll_rad;
    float pitch_rad;
    float yaw_rad;

    Vector3 angular_velocity_b_rad_s;
    float yaw_rate_bias_rad_s;

    float depth_m;

    bool attitude_valid;
    bool heading_valid;
    bool depth_valid;

    Status status;
};


enum class ImuUpdateStatus : uint8_t
{
    INITIALIZING = 0,
    INITIALIZED,
    UPDATED,
    DUPLICATE_TIMESTAMP,
    GAP_TOO_LARGE,
    INVALID_INPUT,
    INVALID_CONFIG,
    NUMERICAL_FAILURE,
    FAULT_LATCHED
};

struct ImuUpdateResult
{
    ImuUpdateStatus status;
    bool accel_correction_used;
    bool magnetometer_correction_used;
};


// ============================================================
// API
// ============================================================

void init(const Config &config);
void reset();

ImuUpdateResult processImuSample(
    const TyrantSensors::ImuSample &sample
);

void processDepthMeasurement(
    const TyrantSensors::DepthMeasurement &measurement
);

bool getState(State &state, uint32_t now_us);
bool initialized();

} // namespace TyrantSimpleEstimator
