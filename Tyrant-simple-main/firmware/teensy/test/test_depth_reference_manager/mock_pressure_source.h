#pragma once

#include <Arduino.h>

#include "sensors/pressure_source.h"


class MockPressureSource :
    public TyrantSensors::PressureSource
{
public:
    void setProducing(bool producing)
    {
        producing_ = producing;
    }
    void setPressurePa(
        float pressure_pa)
    {
        pressure_pa_ =
            pressure_pa;
    }


    void setTemperatureC(
        float temperature_c)
    {
        temperature_c_ =
            temperature_c;
    }


    bool begin() override
    {
        initialized_ = true;
        producing_ = true;
        sample_available_ = false;

        sequence_ = 0;

        stats_ = {
            0,
            0,
            0
        };

        return true;
    }


    void update() override
    {
        if (!initialized_)
        {
            return;
        }


        stats_.read_attempts++;


        if (!producing_)
        {
            return;
        }


        sequence_++;

        sample_.sequence =
            sequence_;

        sample_.timestamp_us =
            micros();

        sample_.pressure_pa =
            pressure_pa_;

        sample_.temperature_c =
            temperature_c_;

        sample_.valid =
            true;


        sample_available_ =
            true;


        stats_.read_successes++;

        stats_.samples_produced++;
    }


    bool takeSample(
        TyrantSensors::PressureSample &sample
    ) override
    {
        if (!sample_available_)
        {
            return false;
        }


        sample =
            sample_;

        sample_available_ =
            false;


        return true;
    }


    TyrantSensors::PressureSourceStats
    getStats() const override
    {
        return stats_;
    }


private:
    bool initialized_ = false;

    bool producing_ = true;

    bool sample_available_ = false;

    uint32_t sequence_ = 0;
    float pressure_pa_ = 101325.0f;
    float temperature_c_ = 25.0f;
    
    TyrantSensors::PressureSample sample_ {};


    TyrantSensors::PressureSourceStats stats_ {
        0,
        0,
        0
    };
};
