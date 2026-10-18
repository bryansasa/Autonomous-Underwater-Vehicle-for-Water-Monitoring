#pragma once

#include <Arduino.h>

#include "sensors/sensor_types.h"


namespace TyrantSensors
{
    class DepthEstimator
    {
    public:
        explicit DepthEstimator(
            float water_density_kg_m3 =
                1025.0f
        );


        bool setSurfacePressure(
            float pressure_pa
        );


        void clearSurfaceReference();


        bool surfaceReferenceValid() const;


        float getSurfacePressure() const;


        bool setWaterDensity(
            float water_density_kg_m3
        );


        float getWaterDensity() const;


        bool estimateDepth(
            const PressureSample &sample,
            float &depth_m
        ) const;

        bool estimateMeasurement(
            const PressureSample &sample,
            DepthMeasurement &measurement
        ) const;


    private:
        static constexpr float GRAVITY_MPS2 =
            9.80665f;


        float surface_pressure_pa_ =
            0.0f;


        float water_density_kg_m3_ =
            1025.0f;


        bool surface_reference_valid_ =
            false;
    };
}
