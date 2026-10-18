#include "sensors/depth_estimator.h"
#include <math.h>

namespace TyrantSensors
{
    DepthEstimator::DepthEstimator(
        float water_density_kg_m3
    )
    {
        setWaterDensity(
            water_density_kg_m3
        );
    }


    bool DepthEstimator::setSurfacePressure(
        float pressure_pa
    )
    {
        if (
            !isfinite(pressure_pa) ||
            pressure_pa <= 0.0f
        )
        {
            return false;
        }


        surface_pressure_pa_ =
            pressure_pa;


        surface_reference_valid_ =
            true;


        return true;
    }


    void DepthEstimator::clearSurfaceReference()
    {
        surface_pressure_pa_ =
            0.0f;


        surface_reference_valid_ =
            false;
    }


    bool DepthEstimator::surfaceReferenceValid() const
    {
        return surface_reference_valid_;
    }


    float DepthEstimator::getSurfacePressure() const
    {
        return surface_pressure_pa_;
    }


    bool DepthEstimator::setWaterDensity(
        float water_density_kg_m3
    )
    {
        if (
            !isfinite(water_density_kg_m3) ||
            water_density_kg_m3 <= 0.0f
        )
        {
            return false;
        }


        water_density_kg_m3_ =
            water_density_kg_m3;


        return true;
    }


    float DepthEstimator::getWaterDensity() const
    {
        return water_density_kg_m3_;
    }

    bool DepthEstimator::estimateDepth(
        const PressureSample &sample,
        float &depth_m
    ) const
    {
        // ========================================================
        // REFERENCE VALIDATION
        // ========================================================

        if (!surface_reference_valid_)
        {
            return false;
        }


        if (
            !isfinite(surface_pressure_pa_) ||
            surface_pressure_pa_ <= 0.0f
        )
        {
            return false;
        }


        // ========================================================
        // SAMPLE VALIDATION
        // ========================================================

        if (!sample.valid)
        {
            return false;
        }


        if (
            !isfinite(sample.pressure_pa) ||
            sample.pressure_pa <= 0.0f
        )
        {
            return false;
        }


        // ========================================================
        // MODEL VALIDATION
        // ========================================================

        if (
            !isfinite(water_density_kg_m3_) ||
            water_density_kg_m3_ <= 0.0f
        )
        {
            return false;
        }


        // ========================================================
        // DEPTH CALCULATION
        // ========================================================

        const float delta_pressure_pa =
            sample.pressure_pa -
            surface_pressure_pa_;


        if (!isfinite(delta_pressure_pa))
        {
            return false;
        }


        const float calculated_depth_m =
            delta_pressure_pa /
            (
                water_density_kg_m3_ *
                GRAVITY_MPS2
            );


        if (!isfinite(calculated_depth_m))
        {
            return false;
        }


        depth_m =
            calculated_depth_m;


        return true;
    }
    bool DepthEstimator::estimateMeasurement(
        const PressureSample &sample,
        DepthMeasurement &measurement
    ) const
    {
        measurement.sequence =
            sample.sequence;

        measurement.timestamp_us =
            sample.timestamp_us;

        measurement.depth_m =
            0.0f;

        measurement.valid =
            false;


        float depth_m = 0.0f;


        if (
            !estimateDepth(
                sample,
                depth_m
            )
        )
        {
            return false;
        }


        measurement.depth_m =
            depth_m;

        measurement.valid =
            true;


        return true;
    }
}
