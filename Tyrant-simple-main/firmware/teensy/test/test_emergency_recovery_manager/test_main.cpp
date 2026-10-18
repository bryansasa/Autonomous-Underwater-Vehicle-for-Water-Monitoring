#include <Arduino.h>
#include <unity.h>

#include "application/emergency_recovery_manager.h"

namespace
{
TyrantEmergency::Config config()
{
    TyrantEmergency::Config cfg {};
    cfg.surface_target_depth_m = 0.15f;
    cfg.surface_tolerance_m = 0.05f;
    cfg.ascent_command = 0.6f;
    cfg.max_runtime_ms = 1000;
    return cfg;
}

TyrantSimpleEstimator::State validState(float depth_m = 1.0f)
{
    TyrantSimpleEstimator::State state {};
    state.depth_m = depth_m;
    state.attitude_valid = true;
    state.heading_valid = true;
    state.depth_valid = true;
    state.status = TyrantSimpleEstimator::Status::RUNNING;
    return state;
}
}

void setUp()
{
    TyrantEmergency::init(config());
}

void tearDown() {}

void test_zero_thrust_policy_latches_without_actuation()
{
    auto state = validState();
    TEST_ASSERT_TRUE(TyrantEmergency::trigger(
        TyrantEmergency::Policy::ZERO_THRUST,
        state,
        100));

    TyrantControl::ManualCommand command {};
    TEST_ASSERT_FALSE(TyrantEmergency::update(state, 200, command));
    TEST_ASSERT_FLOAT_WITHIN(1.0e-6f, 0.0f, command.heave);
    TEST_ASSERT_FALSE(TyrantEmergency::getStatus(200).actuation_requested);
}

void test_controlled_surface_rejects_invalid_depth_state()
{
    auto state = validState();
    state.depth_valid = false;

    TEST_ASSERT_FALSE(TyrantEmergency::trigger(
        TyrantEmergency::Policy::CONTROLLED_SURFACE,
        state,
        100));

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantEmergency::State::FAILED),
        static_cast<uint8_t>(TyrantEmergency::getStatus(100).state));
}

void test_controlled_surface_commands_negative_heave()
{
    auto state = validState(2.0f);
    TEST_ASSERT_TRUE(TyrantEmergency::trigger(
        TyrantEmergency::Policy::CONTROLLED_SURFACE,
        state,
        100));

    TyrantControl::ManualCommand command {};
    TEST_ASSERT_TRUE(TyrantEmergency::update(state, 200, command));
    TEST_ASSERT_FLOAT_WITHIN(1.0e-6f, -0.6f, command.heave);
    TEST_ASSERT_TRUE(TyrantEmergency::getStatus(200).actuation_requested);
}

void test_controlled_surface_completes_near_surface()
{
    auto state = validState(1.0f);
    TEST_ASSERT_TRUE(TyrantEmergency::trigger(
        TyrantEmergency::Policy::CONTROLLED_SURFACE,
        state,
        100));

    state.depth_m = 0.18f;
    TyrantControl::ManualCommand command {};
    TEST_ASSERT_FALSE(TyrantEmergency::update(state, 200, command));
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantEmergency::State::COMPLETE),
        static_cast<uint8_t>(TyrantEmergency::getStatus(200).state));
}

void test_controlled_surface_fails_on_runtime_timeout()
{
    auto state = validState(2.0f);
    TEST_ASSERT_TRUE(TyrantEmergency::trigger(
        TyrantEmergency::Policy::CONTROLLED_SURFACE,
        state,
        100));

    TyrantControl::ManualCommand command {};
    TEST_ASSERT_FALSE(TyrantEmergency::update(state, 1200, command));
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantEmergency::Reason::TIMEOUT),
        static_cast<uint8_t>(TyrantEmergency::getStatus(1200).reason));
}

void test_state_loss_during_surface_fails_closed()
{
    auto state = validState(2.0f);
    TEST_ASSERT_TRUE(TyrantEmergency::trigger(
        TyrantEmergency::Policy::CONTROLLED_SURFACE,
        state,
        100));

    state.attitude_valid = false;
    TyrantControl::ManualCommand command {};
    TEST_ASSERT_FALSE(TyrantEmergency::update(state, 200, command));
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantEmergency::Reason::INVALID_STATE),
        static_cast<uint8_t>(TyrantEmergency::getStatus(200).reason));
}

void setup()
{
    delay(500);
    UNITY_BEGIN();
    RUN_TEST(test_zero_thrust_policy_latches_without_actuation);
    RUN_TEST(test_controlled_surface_rejects_invalid_depth_state);
    RUN_TEST(test_controlled_surface_commands_negative_heave);
    RUN_TEST(test_controlled_surface_completes_near_surface);
    RUN_TEST(test_controlled_surface_fails_on_runtime_timeout);
    RUN_TEST(test_state_loss_during_surface_fails_closed);
    UNITY_END();
}

void loop() {}
