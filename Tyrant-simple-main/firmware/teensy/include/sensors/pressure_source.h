#pragma once

#include <Arduino.h>

#include "sensors/sensor_types.h"


namespace TyrantSensors
{
    struct PressureSourceStats
    {
        uint32_t read_attempts;
        uint32_t read_successes;
        uint32_t samples_produced;
    };


    class PressureSource
    {
    public:
        virtual ~PressureSource() = default;


        virtual bool begin() = 0;

        virtual void update() = 0;


        virtual bool takeSample(
            PressureSample &sample
        ) = 0;


        virtual PressureSourceStats
        getStats() const = 0;
    };
}