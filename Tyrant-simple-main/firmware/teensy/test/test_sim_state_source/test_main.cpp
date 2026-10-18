#include <Arduino.h>
#include <math.h>
#include <unity.h>

#include "simulation/sim_state_source.h"

namespace
{
TyrantSimpleEstimator::State makeValidState()
{
    TyrantSimpleEstimator::State state {};
    state.roll_rad = 0.1f;
    state.pitch_rad = -0.2f;
    state.yaw_rad = 1.0f;
    state.angular_velocity_b_rad_s = {0.01f, 0.02f, 0.03f};
    state.yaw_rate_bias_rad_s = 0.001f;
    state.depth_m = 2.0f;
    state.attitude_valid = true;
    state.heading_valid = true;
    state.depth_valid = true;
    state.status = TyrantSimpleEstimator::Status::RUNNING;
    return state;
}

void resetSource()
{
    TyrantSimulation::initSimStateSource({200000u});
}

void test_no_state_is_invalid()
{
    resetSource();

    TyrantSimpleEstimator::State state {};
    TEST_ASSERT_FALSE(TyrantSimulation::getSimState(state, 1000u));
    TEST_ASSERT_FALSE(state.attitude_valid);
    TEST_ASSERT_FALSE(state.heading_valid);
    TEST_ASSERT_FALSE(state.depth_valid);
}

void test_valid_state_round_trip()
{
    resetSource();

    const auto input = makeValidState();
    TEST_ASSERT_TRUE(TyrantSimulation::acceptSimState(input, 1000u));

    TyrantSimpleEstimator::State output {};
    TEST_ASSERT_TRUE(TyrantSimulation::getSimState(output, 1500u));
    TEST_ASSERT_FLOAT_WITHIN(1.0e-6f, input.yaw_rad, output.yaw_rad);
    TEST_ASSERT_FLOAT_WITHIN(1.0e-6f, input.depth_m, output.depth_m);
}

void test_state_expires()
{
    resetSource();
    TEST_ASSERT_TRUE(TyrantSimulation::acceptSimState(makeValidState(), 1000u));

    TyrantSimpleEstimator::State output {};
    TEST_ASSERT_FALSE(TyrantSimulation::getSimState(output, 201001u));
    TEST_ASSERT_FALSE(output.attitude_valid);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantSimpleEstimator::Status::DEGRADED),
        static_cast<uint8_t>(output.status)
    );
}

void test_wrap_safe_age()
{
    resetSource();
    TEST_ASSERT_TRUE(
        TyrantSimulation::acceptSimState(makeValidState(), 0xFFFFFF00u)
    );

    TyrantSimpleEstimator::State output {};
    TEST_ASSERT_TRUE(TyrantSimulation::getSimState(output, 0x00000020u));
    TEST_ASSERT_EQUAL_UINT32(0x120u, TyrantSimulation::simStateAgeUs(0x20u));
}

void test_nonfinite_state_rejected()
{
    resetSource();
    auto state = makeValidState();
    state.depth_m = NAN;
    TEST_ASSERT_FALSE(TyrantSimulation::acceptSimState(state, 1000u));
}

void test_fault_state_rejected()
{
    resetSource();
    auto state = makeValidState();
    state.status = TyrantSimpleEstimator::Status::FAULT;
    TEST_ASSERT_FALSE(TyrantSimulation::acceptSimState(state, 1000u));
}

void test_zero_timeout_rejects()
{
    TyrantSimulation::initSimStateSource({0u});
    TEST_ASSERT_FALSE(
        TyrantSimulation::acceptSimState(makeValidState(), 1000u)
    );
}
}

void setup()
{
    delay(2000);
    UNITY_BEGIN();

    RUN_TEST(test_no_state_is_invalid);
    RUN_TEST(test_valid_state_round_trip);
    RUN_TEST(test_state_expires);
    RUN_TEST(test_wrap_safe_age);
    RUN_TEST(test_nonfinite_state_rejected);
    RUN_TEST(test_fault_state_rejected);
    RUN_TEST(test_zero_timeout_rejects);

    UNITY_END();
}

void loop()
{
}
