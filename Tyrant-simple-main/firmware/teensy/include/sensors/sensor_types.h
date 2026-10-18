#pragma once

#include <stdint.h>

namespace TyrantSensors
{

// ============================================================
// SENSOR STATE
// ============================================================

enum class SensorState : uint8_t
{
    NOT_INITIALIZED = 0,
    INITIALIZING = 1,
    READY = 2,
    STALE = 3,
    ERROR = 4
};


// ============================================================
// IMU SAMPLE
//
// BODY frame: FRD
// +X forward, +Y starboard/right, +Z down.
// Acceleration is specific force in m/s^2.
// Gyro is angular rate in rad/s.
// ============================================================

struct ImuSample
{
    uint32_t sequence;
    uint64_t timestamp_us;

    float accel_x;
    float accel_y;
    float accel_z;

    float gyro_x;
    float gyro_y;
    float gyro_z;

    int16_t mag_x_lsb;
    int16_t mag_y_lsb;
    int16_t mag_z_lsb;

    uint32_t mag_sequence;

    bool valid;
    bool mag_valid;
    bool mag_updated;
};


// ============================================================
// PRESSURE / DEPTH
// ============================================================

struct PressureSample
{
    uint32_t sequence;
    uint64_t timestamp_us;
    float pressure_pa;
    float temperature_c;
    bool valid;
};

struct DepthMeasurement
{
    uint32_t sequence;
    uint64_t timestamp_us;
    float depth_m; // positive down
    bool valid;
};


// ============================================================
// GENERIC SENSOR HEALTH
// ============================================================

struct SensorHealth
{
    SensorState state;
    uint32_t sample_count;
    uint32_t error_count;
    uint64_t last_update_us;
    bool valid;
};

} // namespace TyrantSensors
