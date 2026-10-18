#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <MS5837.h>

#include "sensors/pressure_source.h"


namespace TyrantSensors
{

// ============================================================
// FULLDEPTH PRESSURE SOURCE
//
// FullDepth hardware used in this project exposes an MS5837
// pressure sensor over I2C. This adapter publishes raw absolute
// pressure and temperature only. Surface-zero and pressure-to-
// depth conversion remain owned by DepthEstimator.
// ============================================================

class FullDepthPressureSource :
    public PressureSource
{
public:
    FullDepthPressureSource(
        TwoWire &wire,
        uint32_t i2c_clock_hz,
        uint32_t sample_period_us
    );


    bool begin() override;

    void update() override;


    bool takeSample(
        PressureSample &sample
    ) override;


    PressureSourceStats
    getStats() const override;


private:
    bool sampleDue(
        uint32_t now_us
    ) const;


    TwoWire &wire_;

    MS5837 sensor_;

    uint32_t i2c_clock_hz_;
    uint32_t sample_period_us_;

    uint32_t last_read_us_ = 0;
    uint32_t sequence_ = 0;

    bool initialized_ = false;
    bool sample_available_ = false;

    PressureSample sample_ {};

    PressureSourceStats stats_ {
        0,
        0,
        0
    };
};

} // namespace TyrantSensors
