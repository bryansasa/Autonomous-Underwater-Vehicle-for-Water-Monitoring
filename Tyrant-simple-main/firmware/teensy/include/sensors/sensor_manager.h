#pragma once

#include <Arduino.h>

#include "sensors/sensor_types.h"
#include "sensors/imu_source.h"
#include "sensors/pressure_source.h"

namespace TyrantSensors
{
    // ========================================================
    // LIFECYCLE
    // ========================================================
    void setImuSource(
        ImuSource &source
    );

    void setPressureSource(
        PressureSource &source
    );

    void init();

    void update();


    // ========================================================
    // SAMPLE SNAPSHOTS
    //
    // Non-destructive.
    // Intended for telemetry, diagnostics, and monitoring.
    // ========================================================

    bool getImuSnapshot(
        ImuSample &sample
    );

    bool getPressureSnapshot(
        PressureSample &sample
    );


    // ========================================================
    // SAMPLE STREAM ACCESS
    //
    // Destructive for the "new sample" flag.
    // Intended for estimator / processing consumers.
    // ========================================================

    bool takeImuSample(
        ImuSample &sample
    );

    bool takePressureSample(
        PressureSample &sample
    );


    // ========================================================
    // HEALTH ACCESS
    // ========================================================

    SensorHealth getImuHealth();
    ImuSourceStats getImuStats();

    SensorHealth getPressureHealth();
    PressureSourceStats getPressureStats();

    // ========================================================
    // READINESS
    // ========================================================

    bool imuHealthy();

    bool pressureHealthy();

    bool requiredSensorsHealthy();

    // ========================================================
    // DEPTH PROCESSING
    // ========================================================

    bool setDepthSurfaceReference();

    void clearDepthSurfaceReference();
    bool depthSurfaceReferenceValid();
    float depthSurfacePressurePa();
    bool getDepthSnapshot(
        DepthMeasurement &measurement
    );
    bool takeDepthMeasurement(
        DepthMeasurement &measurement
    );
}
