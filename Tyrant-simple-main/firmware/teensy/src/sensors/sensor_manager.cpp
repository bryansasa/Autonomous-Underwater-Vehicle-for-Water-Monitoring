#include "sensors/sensor_manager.h"
#include <Arduino.h>
#include "config/sensor_config.h"
#include "sensors/depth_estimator.h"
#include <math.h>

namespace
{
    TyrantSensors::DepthEstimator
        depth_estimator {
            TyrantSensorConfig::
                DEPTH_WATER_DENSITY_KG_M3
        };


    TyrantSensors::DepthMeasurement
        latest_depth {};
    bool depth_snapshot_available =
        false;
    bool depth_measurement_available =
        false;

    TyrantSensors::ImuSource *imu_source =
        nullptr;

    TyrantSensors::PressureSource *pressure_source =
        nullptr;


    TyrantSensors::ImuSample latest_imu {};
    
    TyrantSensors::PressureSample latest_pressure {};


    TyrantSensors::SensorHealth imu_health {
        TyrantSensors::SensorState::NOT_INITIALIZED,
        0,
        0,
        0,
        false
    };

    TyrantSensors::SensorHealth pressure_health {
        TyrantSensors::SensorState::NOT_INITIALIZED,
        0,
        0,
        0,
        false
    };


    bool imu_snapshot_available =
        false;

    bool pressure_snapshot_available =
        false;
    bool imu_sample_available =
        false;
    bool pressure_sample_available =
        false;
    bool imuSampleUsable(
        const TyrantSensors::ImuSample &sample
    )
    {
        return (
            sample.valid &&

            isfinite(sample.accel_x) &&
            isfinite(sample.accel_y) &&
            isfinite(sample.accel_z) &&

            isfinite(sample.gyro_x) &&
            isfinite(sample.gyro_y) &&
            isfinite(sample.gyro_z)
        );
    }


    bool pressureSampleUsable(
        const TyrantSensors::PressureSample &sample
    )
    {
        return (
            sample.valid &&
            isfinite(sample.pressure_pa) &&
            sample.pressure_pa > 0.0f
        );
    }
}


namespace TyrantSensors
{
    bool setDepthSurfaceReference()
    {
        if (
            pressure_health.state !=
                SensorState::READY
        )
        {
            return false;
        }


        if (
            !pressure_health.valid ||
            !latest_pressure.valid
        )
        {
            return false;
        }


        if (
            !depth_estimator.setSurfacePressure(
                latest_pressure.pressure_pa
            )
        )
        {
            return false;
        }


        DepthMeasurement measurement {};


        depth_estimator.estimateMeasurement(
            latest_pressure,
            measurement
        );


        latest_depth =
            measurement;

        depth_snapshot_available =
            true;


        depth_measurement_available =
            measurement.valid;


        return true;
    }


    void clearDepthSurfaceReference()
    {
        depth_estimator.clearSurfaceReference();


        latest_depth.depth_m =
            0.0f;

        latest_depth.valid =
            false;

        depth_snapshot_available =
            true;

        depth_measurement_available =
             false;
    }


    bool depthSurfaceReferenceValid()
    {
        return depth_estimator
            .surfaceReferenceValid();
    }
    
    
    float depthSurfacePressurePa()
    {
        if (
            !depth_estimator
                .surfaceReferenceValid()
        )
        {
            return 0.0f;
        }

        return depth_estimator
            .getSurfacePressure();
    }

    bool getDepthSnapshot(
        DepthMeasurement &measurement
    )
    {
        if (!depth_snapshot_available)
        {
            return false;
        }


        measurement =
            latest_depth;


        return true;
    }


    bool takeDepthMeasurement(
        DepthMeasurement &measurement
    )
    {
        if (!depth_measurement_available)
        {
            return false;
        }


        measurement =
            latest_depth;


        depth_measurement_available =
            false;


        return true;
    }

    void setImuSource(
        ImuSource &source
    )
    {
        imu_source =
            &source;
    }


    void setPressureSource(
        PressureSource &source
    )
    {
        pressure_source =
            &source;
    }


    void init()
    {
        /*
         * Reset cached samples.
         */
        latest_imu =
            ImuSample {};

        latest_pressure =
            PressureSample {};


        imu_snapshot_available =
            false;

        pressure_snapshot_available =
            false;


        imu_sample_available =
            false;

        pressure_sample_available =
            false;


        latest_depth = {};


        depth_snapshot_available =
            false;

        depth_measurement_available =
            false;

        depth_estimator.clearSurfaceReference();

        /*
         * Reset health state.
         */
        imu_health = {
            SensorState::NOT_INITIALIZED,
            0,
            0,
            0,
            false
        };

        pressure_health = {
            SensorState::NOT_INITIALIZED,
            0,
            0,
            0,
            false
        };


        /*
         * Initialize IMU source.
         */
        if (imu_source == nullptr)
        {
            imu_health.state =
                SensorState::ERROR;

            imu_health.error_count++;

            imu_health.valid =
                false;
        }
        else
        {
            imu_health.state =
                SensorState::INITIALIZING;

            if (!imu_source->begin())
            {
                imu_health.state =
                    SensorState::ERROR;

                imu_health.error_count++;

                imu_health.valid =
                    false;
            }
        }


        /*
         * Initialize pressure source.
         */
        if (pressure_source == nullptr)
        {
            pressure_health.state =
                SensorState::ERROR;

            pressure_health.error_count++;

            pressure_health.valid =
                false;
        }
        else
        {
            pressure_health.state =
                SensorState::INITIALIZING;

            if (!pressure_source->begin())
            {
                pressure_health.state =
                    SensorState::ERROR;

                pressure_health.error_count++;

                pressure_health.valid =
                    false;
            }
        }
    }


    void update()
    {
        /*
         * =========================
         * IMU
         * =========================
         */
        if (imu_source != nullptr)
        {
            imu_source->update();


            ImuSample new_imu_sample {};


           if (
            imu_source->takeSample(
                new_imu_sample
            )
        )
        {
            const bool usable =
                imuSampleUsable(
                    new_imu_sample
                );


            new_imu_sample.valid =
                usable;


            latest_imu =
                new_imu_sample;


            // Telemetry may inspect even an invalid sample.
            imu_snapshot_available =
                true;


            // Estimator stream receives usable samples only.
            imu_sample_available =
                usable;


            imu_health.state =
                SensorState::READY;

            imu_health.sample_count++;

            imu_health.last_update_us =
                new_imu_sample.timestamp_us;

            imu_health.valid =
                usable;


            if (!usable)
            {
                imu_health.error_count++;
            }
        }
        }


        /*
         * IMU stale detection.
         *
         * micros() is a 32-bit counter.
         * Unsigned subtraction keeps this
         * wrap-safe.
         */
        if (
            imu_health.state ==
                SensorState::READY
        )
        {
            const uint32_t now_us =
                micros();

            const uint32_t last_update_us =
                static_cast<uint32_t>(
                    imu_health.last_update_us
                );

            const uint32_t age_us =
                now_us -
                last_update_us;


        if (
            age_us >
            TyrantSensorConfig::
                IMU_STALE_TIMEOUT_US
        )
        {
            imu_health.state =
                SensorState::STALE;

            imu_health.valid =
                false;

            imu_sample_available =
                false;
        }
        }


        /*
         * =========================
         * PRESSURE
         * =========================
         */
        if (pressure_source != nullptr)
        {
            pressure_source->update();


            PressureSample new_pressure_sample {};


            if (
            pressure_source->takeSample(
                new_pressure_sample
            )
        )
        {
            const bool usable =
                pressureSampleUsable(
                    new_pressure_sample
                );


            new_pressure_sample.valid =
                usable;


            latest_pressure =
                new_pressure_sample;


            pressure_snapshot_available =
                true;

            pressure_sample_available =
                usable;


            pressure_health.state =
                SensorState::READY;

            pressure_health.sample_count++;

            pressure_health.last_update_us =
                new_pressure_sample.timestamp_us;

            pressure_health.valid =
                usable;


            if (!usable)
            {
                pressure_health.error_count++;
            }


            DepthMeasurement new_depth {};


            depth_estimator.estimateMeasurement(
                new_pressure_sample,
                new_depth
            );


            latest_depth =
                new_depth;


            depth_snapshot_available =
                true;

            depth_measurement_available =
                new_depth.valid;
        }
        }


        /*
         * Pressure stale detection.
         */
        if (
            pressure_health.state ==
                SensorState::READY
        )
        {
            const uint32_t now_us =
                micros();

            const uint32_t last_update_us =
                static_cast<uint32_t>(
                    pressure_health.last_update_us
                );

            const uint32_t age_us =
                now_us -
                last_update_us;


        if (
            age_us >
            TyrantSensorConfig::
                PRESSURE_STALE_TIMEOUT_US
        )
        {
            pressure_health.state =
                SensorState::STALE;

            pressure_health.valid =
                false;

            pressure_sample_available =
                false;


            latest_depth.valid =
                false;

            depth_snapshot_available =
                true;

            depth_measurement_available =
                false;
        }
        }
    }

    bool getImuSnapshot(
        ImuSample &sample
    )
    {
        if (!imu_snapshot_available)
        {
            return false;
        }


        sample =
            latest_imu;


        return true;
    }


    bool takeImuSample(
        ImuSample &sample
    )
    {
        if (!imu_sample_available)
        {
            return false;
        }


        sample =
            latest_imu;


        imu_sample_available =
            false;


        return true;
    }



    bool getPressureSnapshot(
    PressureSample &sample
)
{
    if (!pressure_snapshot_available)
    {
        return false;
    }


    sample =
        latest_pressure;


    return true;
}


    bool takePressureSample(
        PressureSample &sample
    )
    {
        if (!pressure_sample_available)
        {
            return false;
        }


        sample =
            latest_pressure;


        pressure_sample_available =
            false;


        return true;
    }


    SensorHealth getImuHealth()
    {
        return imu_health;
    }


    ImuSourceStats getImuStats()
    {
        if (imu_source == nullptr)
        {
            return {};
        }

        return imu_source->getStats();
    }


    SensorHealth getPressureHealth()
    {
        return pressure_health;
    }


    PressureSourceStats getPressureStats()
    {
        if (pressure_source == nullptr)
        {
            return {};
        }

        return pressure_source->getStats();
    }


    bool imuHealthy()
    {
        return (
            imu_health.state ==
                SensorState::READY &&
            imu_health.valid
        );
    }


    bool pressureHealthy()
    {
        return (
            pressure_health.state ==
                SensorState::READY &&
            pressure_health.valid
        );
    }


    bool requiredSensorsHealthy()
    {
        return (
            imuHealthy() &&
            pressureHealthy()
        );
    }

}