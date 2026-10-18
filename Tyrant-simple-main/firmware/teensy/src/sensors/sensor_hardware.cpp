#include "sensors/sensor_hardware.h"

#include <Arduino.h>
#include <Wire.h>

#include "config/sensor_config.h"
#include "sensors/drivers/fulldepth_pressure_source.h"
#include "sensors/drivers/hwt905_driver.h"
#include "sensors/sensor_manager.h"


namespace
{

// ============================================================
// IMU HARDWARE
// ============================================================

// Verified hardware bring-up UART.
TyrantSensors::Hwt905Driver hwt905(
    Serial1,
    TyrantSensorConfig::HWT905_BAUD,
    TyrantSensorConfig::HWT905_MOUNTING
);


// ============================================================
// DEPTH / PRESSURE HARDWARE
// ============================================================

TyrantSensors::FullDepthPressureSource full_depth(
    Wire,
    TyrantSensorConfig::FULLDEPTH_I2C_CLOCK_HZ,
    TyrantSensorConfig::FULLDEPTH_SAMPLE_PERIOD_US
);

} // namespace


namespace TyrantSensors
{

void bindProductionSensors()
{
    setImuSource(
        hwt905
    );

    setPressureSource(
        full_depth
    );
}

} // namespace TyrantSensors
