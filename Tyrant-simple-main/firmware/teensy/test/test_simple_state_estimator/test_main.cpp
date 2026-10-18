#include <Arduino.h>
#include <unity.h>

#include "config/simple_estimator_config.h"
#include "estimation/simple_state_estimator.h"

namespace
{
constexpr float DEG_TO_RAD_F= 0.017453292519943295f;

TyrantSensors::ImuSample stationarySample(
    uint32_t sequence,
    uint32_t timestamp_us,
    float gyro_z = 0.0f)
{
    TyrantSensors::ImuSample sample {};
    sample.sequence = sequence;
    sample.timestamp_us = timestamp_us;

    // Approximately roll = -5 deg in BODY FRD.
    sample.accel_x = 0.0f;
    sample.accel_y = 0.8549978f;
    sample.accel_z = -9.7693329f;

    sample.gyro_x = 0.0f;
    sample.gyro_y = 0.0f;
    sample.gyro_z = gyro_z;

    // Representative stable field from hardware after mounting mapping.
    sample.mag_x_lsb = 316;
    sample.mag_y_lsb = -3122;
    sample.mag_z_lsb = -632;
    sample.mag_sequence = sequence;

    sample.valid = true;
    sample.mag_valid = true;
    sample.mag_updated = true;
    return sample;
}

void initializeEstimator(uint32_t &sequence, uint32_t &timestamp_us)
{
    TyrantSimpleEstimator::init(
        TyrantSimpleEstimatorConfig::makeDevelopmentConfig());

    for (size_t i = 0; i < 60; ++i)
    {
        ++sequence;
        timestamp_us += 100000U;
        (void)TyrantSimpleEstimator::processImuSample(
            stationarySample(sequence, timestamp_us));
    }
}

void test_stationary_state_stays_bounded()
{
    uint32_t sequence = 0;
    uint32_t timestamp_us = 0;
    initializeEstimator(sequence, timestamp_us);

    for (size_t i = 0; i < 600; ++i)
    {
        ++sequence;
        timestamp_us += 100000U;
        (void)TyrantSimpleEstimator::processImuSample(
            stationarySample(sequence, timestamp_us));
    }

    TyrantSimpleEstimator::State state {};
    TEST_ASSERT_TRUE(
        TyrantSimpleEstimator::getState(state, timestamp_us));

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantSimpleEstimator::Status::RUNNING),
        static_cast<uint8_t>(state.status));

    TEST_ASSERT_FLOAT_WITHIN(1.0f * DEG_TO_RAD, -5.0f * DEG_TO_RAD, state.roll_rad);
    TEST_ASSERT_FLOAT_WITHIN(1.0f * DEG_TO_RAD, 0.0f, state.pitch_rad);
    TEST_ASSERT_TRUE(isfinite(state.yaw_rad));
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, state.angular_velocity_b_rad_s.z);
}

void test_yaw_filter_learns_residual_rate_bias()
{
    uint32_t sequence = 0;
    uint32_t timestamp_us = 0;
    initializeEstimator(sequence, timestamp_us);

    for (size_t i = 0; i < 1200; ++i)
    {
        ++sequence;
        timestamp_us += 100000U;
        (void)TyrantSimpleEstimator::processImuSample(
            stationarySample(sequence, timestamp_us, 0.01f));
    }

    TyrantSimpleEstimator::State state {};
    TEST_ASSERT_TRUE(
        TyrantSimpleEstimator::getState(state, timestamp_us));

    TEST_ASSERT_FLOAT_WITHIN(0.003f, 0.01f, state.yaw_rate_bias_rad_s);
}


void test_requires_stationary_window_before_running()
{
    TyrantSimpleEstimator::init(
        TyrantSimpleEstimatorConfig::makeDevelopmentConfig());

    uint32_t timestamp_us = 0;
    for (uint32_t sequence = 1; sequence <= 10; ++sequence)
    {
        timestamp_us += 100000U;
        const auto result = TyrantSimpleEstimator::processImuSample(
            stationarySample(sequence, timestamp_us));

        TEST_ASSERT_EQUAL_UINT8(
            static_cast<uint8_t>(TyrantSimpleEstimator::ImuUpdateStatus::INITIALIZING),
            static_cast<uint8_t>(result.status));
    }

    TEST_ASSERT_FALSE(TyrantSimpleEstimator::initialized());

    TyrantSimpleEstimator::State state {};
    TEST_ASSERT_FALSE(TyrantSimpleEstimator::getState(state, timestamp_us));
}

void test_duplicate_timestamp_is_rejected_without_latching_fault()
{
    uint32_t sequence = 0;
    uint32_t timestamp_us = 0;
    initializeEstimator(sequence, timestamp_us);

    ++sequence;
    const auto duplicate = TyrantSimpleEstimator::processImuSample(
        stationarySample(sequence, timestamp_us));

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantSimpleEstimator::ImuUpdateStatus::DUPLICATE_TIMESTAMP),
        static_cast<uint8_t>(duplicate.status));

    ++sequence;
    timestamp_us += 100000U;
    const auto recovered = TyrantSimpleEstimator::processImuSample(
        stationarySample(sequence, timestamp_us));

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantSimpleEstimator::ImuUpdateStatus::UPDATED),
        static_cast<uint8_t>(recovered.status));
}

void test_gap_too_large_is_reported_and_next_sample_can_recover()
{
    uint32_t sequence = 0;
    uint32_t timestamp_us = 0;
    initializeEstimator(sequence, timestamp_us);

    ++sequence;
    timestamp_us += 300000U;
    const auto gap = TyrantSimpleEstimator::processImuSample(
        stationarySample(sequence, timestamp_us));

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantSimpleEstimator::ImuUpdateStatus::GAP_TOO_LARGE),
        static_cast<uint8_t>(gap.status));

    ++sequence;
    timestamp_us += 100000U;
    const auto recovered = TyrantSimpleEstimator::processImuSample(
        stationarySample(sequence, timestamp_us));

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantSimpleEstimator::ImuUpdateStatus::UPDATED),
        static_cast<uint8_t>(recovered.status));
}

void test_heading_freshness_degrades_without_new_magnetometer()
{
    uint32_t sequence = 0;
    uint32_t timestamp_us = 0;
    initializeEstimator(sequence, timestamp_us);

    for (size_t i = 0; i < 11; ++i)
    {
        ++sequence;
        timestamp_us += 100000U;
        auto sample = stationarySample(sequence, timestamp_us);
        sample.mag_valid = false;
        sample.mag_updated = false;
        (void)TyrantSimpleEstimator::processImuSample(sample);
    }

    TyrantSimpleEstimator::State state {};
    TEST_ASSERT_TRUE(TyrantSimpleEstimator::getState(state, timestamp_us));
    TEST_ASSERT_TRUE(state.attitude_valid);
    TEST_ASSERT_FALSE(state.heading_valid);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantSimpleEstimator::Status::DEGRADED),
        static_cast<uint8_t>(state.status));
}

void test_depth_freshness_is_independent_of_heading()
{
    uint32_t sequence = 0;
    uint32_t timestamp_us = 0;
    initializeEstimator(sequence, timestamp_us);

    TyrantSensors::DepthMeasurement depth {};
    depth.sequence = 1;
    depth.timestamp_us = timestamp_us;
    depth.depth_m = 2.5f;
    depth.valid = true;

    TyrantSimpleEstimator::processDepthMeasurement(depth);

    TyrantSimpleEstimator::State state {};
    TEST_ASSERT_TRUE(TyrantSimpleEstimator::getState(state, timestamp_us));
    TEST_ASSERT_TRUE(state.depth_valid);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 2.5f, state.depth_m);

    TEST_ASSERT_TRUE(TyrantSimpleEstimator::getState(
        state,
        timestamp_us + 2000001U));
    TEST_ASSERT_FALSE(state.depth_valid);
}

void test_invalid_config_is_rejected()
{
    auto config = TyrantSimpleEstimatorConfig::makeDevelopmentConfig();
    config.max_dt_s = 0.0f;
    TyrantSimpleEstimator::init(config);

    const auto result = TyrantSimpleEstimator::processImuSample(
        stationarySample(1, 100000U));

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantSimpleEstimator::ImuUpdateStatus::INVALID_CONFIG),
        static_cast<uint8_t>(result.status));

    TyrantSimpleEstimator::State state {};
    TEST_ASSERT_FALSE(TyrantSimpleEstimator::getState(state, 100000U));
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantSimpleEstimator::Status::FAULT),
        static_cast<uint8_t>(state.status));
}

}

void setup()
{
    delay(2000);
    UNITY_BEGIN();
    RUN_TEST(test_stationary_state_stays_bounded);
    RUN_TEST(test_yaw_filter_learns_residual_rate_bias);
    RUN_TEST(test_requires_stationary_window_before_running);
    RUN_TEST(test_duplicate_timestamp_is_rejected_without_latching_fault);
    RUN_TEST(test_gap_too_large_is_reported_and_next_sample_can_recover);
    RUN_TEST(test_heading_freshness_degrades_without_new_magnetometer);
    RUN_TEST(test_depth_freshness_is_independent_of_heading);
    RUN_TEST(test_invalid_config_is_rejected);
    UNITY_END();
}

void loop() {}
