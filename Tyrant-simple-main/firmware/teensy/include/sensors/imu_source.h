#pragma once

#include "sensors/sensor_types.h"


namespace TyrantSensors
{
    struct ImuSourceStats
    {
        uint32_t bytes_received;
        uint32_t register_updates;
        uint32_t samples_produced;
        uint32_t samples_dropped;
    };
    class ImuSource
    {
    public:
        virtual ~ImuSource() = default;


        virtual bool begin() = 0;

        virtual void update() = 0;


        virtual bool takeSample(
            ImuSample &sample
        ) = 0;
        virtual ImuSourceStats getStats() const = 0;
    };

}