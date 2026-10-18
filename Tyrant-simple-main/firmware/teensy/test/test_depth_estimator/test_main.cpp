#include <Arduino.h>
#include <unity.h>

#include "sensors/depth_estimator.h"


constexpr float TEST_SURFACE_PRESSURE_PA =
    100000.0f;

constexpr float TEST_WATER_DENSITY =
    1025.0f;

constexpr float TEST_GRAVITY =
    9.80665f;


TyrantSensors::PressureSample
makePressureSampleForDepth(
    float depth_m
)
{
    TyrantSensors::PressureSample sample {};


    sample.pressure_pa =
        TEST_SURFACE_PRESSURE_PA +
        (
            TEST_WATER_DENSITY *
            TEST_GRAVITY *
            depth_m
        );


    sample.temperature_c =
        25.0f;


    sample.valid =
        true;


    return sample;
}


void test_no_surface_reference_rejected()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    auto sample =
        makePressureSampleForDepth(
            1.0f
        );


    float depth_m = 0.0f;


    TEST_ASSERT_FALSE(
        estimator.estimateDepth(
            sample,
            depth_m
        )
    );
}


void test_surface_pressure_is_zero_depth()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    TEST_ASSERT_TRUE(
        estimator.setSurfacePressure(
            TEST_SURFACE_PRESSURE_PA
        )
    );


    auto sample =
        makePressureSampleForDepth(
            0.0f
        );


    float depth_m = 0.0f;


    TEST_ASSERT_TRUE(
        estimator.estimateDepth(
            sample,
            depth_m
        )
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        0.0f,
        depth_m
    );
}


void test_one_meter_depth()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    estimator.setSurfacePressure(
        TEST_SURFACE_PRESSURE_PA
    );


    auto sample =
        makePressureSampleForDepth(
            1.0f
        );


    float depth_m = 0.0f;


    TEST_ASSERT_TRUE(
        estimator.estimateDepth(
            sample,
            depth_m
        )
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        1.0f,
        depth_m
    );
}


void test_two_meter_depth()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    estimator.setSurfacePressure(
        TEST_SURFACE_PRESSURE_PA
    );


    auto sample =
        makePressureSampleForDepth(
            2.0f
        );


    float depth_m = 0.0f;


    TEST_ASSERT_TRUE(
        estimator.estimateDepth(
            sample,
            depth_m
        )
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        2.0f,
        depth_m
    );
}


void test_invalid_pressure_sample_rejected()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    estimator.setSurfacePressure(
        TEST_SURFACE_PRESSURE_PA
    );


    auto sample =
        makePressureSampleForDepth(
            1.0f
        );


    sample.valid =
        false;


    float depth_m = 0.0f;


    TEST_ASSERT_FALSE(
        estimator.estimateDepth(
            sample,
            depth_m
        )
    );
}


void test_negative_depth_is_not_clamped()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    estimator.setSurfacePressure(
        TEST_SURFACE_PRESSURE_PA
    );


    auto sample =
        makePressureSampleForDepth(
            -0.1f
        );


    float depth_m = 0.0f;


    TEST_ASSERT_TRUE(
        estimator.estimateDepth(
            sample,
            depth_m
        )
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        -0.1f,
        depth_m
    );
}

void test_depth_measurement_metadata()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    estimator.setSurfacePressure(
        TEST_SURFACE_PRESSURE_PA
    );


    auto sample =
        makePressureSampleForDepth(
            2.0f
        );


    sample.sequence =
        42;

    sample.timestamp_us =
        1234567;


    TyrantSensors::DepthMeasurement
        measurement {};


    TEST_ASSERT_TRUE(
        estimator.estimateMeasurement(
            sample,
            measurement
        )
    );


    TEST_ASSERT_EQUAL_UINT32(
        42,
        measurement.sequence
    );


    TEST_ASSERT_EQUAL_UINT64(
        1234567,
        measurement.timestamp_us
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        2.0f,
        measurement.depth_m
    );


    TEST_ASSERT_TRUE(
        measurement.valid
    );
}

void test_invalid_depth_measurement()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    estimator.setSurfacePressure(
        TEST_SURFACE_PRESSURE_PA
    );


    auto sample =
        makePressureSampleForDepth(
            1.0f
        );


    sample.sequence =
        7;

    sample.timestamp_us =
        500000;

    sample.valid =
        false;


    TyrantSensors::DepthMeasurement
        measurement {};


    TEST_ASSERT_FALSE(
        estimator.estimateMeasurement(
            sample,
            measurement
        )
    );


    TEST_ASSERT_FALSE(
        measurement.valid
    );


    TEST_ASSERT_EQUAL_UINT32(
        7,
        measurement.sequence
    );


    TEST_ASSERT_EQUAL_UINT64(
        500000,
        measurement.timestamp_us
    );
}

void test_infinite_surface_pressure_rejected()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    TEST_ASSERT_FALSE(
        estimator.setSurfacePressure(
            INFINITY
        )
    );


    TEST_ASSERT_FALSE(
        estimator.surfaceReferenceValid()
    );
}

void test_nan_surface_pressure_rejected()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    TEST_ASSERT_FALSE(
        estimator.setSurfacePressure(
            NAN
        )
    );


    TEST_ASSERT_FALSE(
        estimator.surfaceReferenceValid()
    );
}

void test_nan_water_density_rejected()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    const float original_density =
        estimator.getWaterDensity();


    TEST_ASSERT_FALSE(
        estimator.setWaterDensity(
            NAN
        )
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        original_density,
        estimator.getWaterDensity()
    );
}

void test_nan_pressure_sample_rejected()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    TEST_ASSERT_TRUE(
        estimator.setSurfacePressure(
            TEST_SURFACE_PRESSURE_PA
        )
    );


    auto sample =
        makePressureSampleForDepth(
            1.0f
        );


    sample.pressure_pa =
        NAN;

    sample.valid =
        true;


    float depth_m = 123.0f;


    TEST_ASSERT_FALSE(
        estimator.estimateDepth(
            sample,
            depth_m
        )
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        123.0f,
        depth_m
    );
}

void test_infinite_pressure_sample_rejected()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    TEST_ASSERT_TRUE(
        estimator.setSurfacePressure(
            TEST_SURFACE_PRESSURE_PA
        )
    );


    auto sample =
        makePressureSampleForDepth(
            1.0f
        );


    sample.pressure_pa =
        INFINITY;

    sample.valid =
        true;


    float depth_m = 123.0f;


    TEST_ASSERT_FALSE(
        estimator.estimateDepth(
            sample,
            depth_m
        )
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        123.0f,
        depth_m
    );
}
void test_nan_pressure_produces_invalid_measurement()
{
    TyrantSensors::DepthEstimator estimator(
        TEST_WATER_DENSITY
    );


    TEST_ASSERT_TRUE(
        estimator.setSurfacePressure(
            TEST_SURFACE_PRESSURE_PA
        )
    );


    auto sample =
        makePressureSampleForDepth(
            1.0f
        );


    sample.sequence =
        99;

    sample.timestamp_us =
        7654321;

    sample.pressure_pa =
        NAN;

    sample.valid =
        true;


    TyrantSensors::DepthMeasurement
        measurement {};


    TEST_ASSERT_FALSE(
        estimator.estimateMeasurement(
            sample,
            measurement
        )
    );


    TEST_ASSERT_FALSE(
        measurement.valid
    );


    TEST_ASSERT_FLOAT_WITHIN(
        0.001f,
        0.0f,
        measurement.depth_m
    );


    TEST_ASSERT_EQUAL_UINT32(
        99,
        measurement.sequence
    );


    TEST_ASSERT_EQUAL_UINT64(
        7654321,
        measurement.timestamp_us
    );
}

void setup()
{
    delay(2000);


    UNITY_BEGIN();


    RUN_TEST(
        test_no_surface_reference_rejected
    );


    RUN_TEST(
        test_surface_pressure_is_zero_depth
    );


    RUN_TEST(
        test_one_meter_depth
    );


    RUN_TEST(
        test_two_meter_depth
    );


    RUN_TEST(
        test_invalid_pressure_sample_rejected
    );


    RUN_TEST(
        test_negative_depth_is_not_clamped
    );

    RUN_TEST(
        test_depth_measurement_metadata
    );


    RUN_TEST(
        test_invalid_depth_measurement
    );
    RUN_TEST(
        test_nan_surface_pressure_rejected
    );


    RUN_TEST(
        test_infinite_surface_pressure_rejected
    );


    RUN_TEST(
        test_nan_water_density_rejected
    );


    RUN_TEST(
        test_nan_pressure_sample_rejected
    );


    RUN_TEST(
        test_infinite_pressure_sample_rejected
    );


    RUN_TEST(
        test_nan_pressure_produces_invalid_measurement
    );

    UNITY_END();
}


void loop()
{
}
