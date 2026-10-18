#pragma once

#include <Arduino.h>
#include "sensors/imu_mounting.h"

namespace TyrantSensorConfig
{

// ============================================================
// HWT905
//
// Hardware bring-up used 9600 baud and the verified mounting:
// sensor X -> body +X
// sensor Y -> body -Y
// sensor Z -> body -Z
// ============================================================

constexpr uint32_t HWT905_BAUD = 9600;

constexpr TyrantSensors::ImuMounting HWT905_MOUNTING {
    TyrantSensors::ImuAxis::POS_X,
    TyrantSensors::ImuAxis::NEG_Y,
    TyrantSensors::ImuAxis::NEG_Z
};

// Observed coherent HWT905 sample interval is roughly 100 ms.
constexpr uint64_t IMU_STALE_TIMEOUT_US = 500000ULL;

// ============================================================
// FULLDEPTH / MS5837
//
// Production hardware uses the default Teensy Wire bus.
// MS5837 read() is blocking, so keep the production cadence
// deliberately modest while validating the complete stack.
// ============================================================

constexpr uint32_t FULLDEPTH_I2C_CLOCK_HZ = 100000U;
constexpr uint32_t FULLDEPTH_SAMPLE_PERIOD_US = 200000U; // 5 Hz

// Development baseline targets seawater. For freshwater tank
// characterization, temporarily use approximately 997 kg/m^3.
constexpr float DEPTH_WATER_DENSITY_KG_M3 = 1025.0f;

constexpr uint32_t PRESSURE_STALE_TIMEOUT_US = 1000000U;

} // namespace TyrantSensorConfig
