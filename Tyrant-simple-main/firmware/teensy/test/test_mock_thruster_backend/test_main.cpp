#include <Arduino.h>
#include <math.h>
#include <unity.h>

#include "actuation/mock_thruster_backend.h"

void setUp()
{
    TyrantActuation::initMockThrusterBackend();
}

void tearDown() {}

void test_init_is_neutral_and_invalid()
{
    const auto state = TyrantActuation::getMockThrusterState();

    TEST_ASSERT_EQUAL_UINT32(0, state.apply_count);
    TEST_ASSERT_FALSE(state.command.valid);
    TEST_ASSERT_FALSE(state.command.enabled);
}

void test_valid_enabled_command_is_stored()
{
    auto command = TyrantControl::makeNeutralThrusterCommand(
        12,
        TyrantControl::ThrusterAllocationStatus::OK,
        true);
    command.enabled = true;
    command.value[0] = 0.3f;
    command.value[7] = -0.2f;

    TyrantActuation::applyMockThrusterCommand(command);

    const auto state = TyrantActuation::getMockThrusterState();
    TEST_ASSERT_EQUAL_UINT32(1, state.apply_count);
    TEST_ASSERT_TRUE(state.command.valid);
    TEST_ASSERT_TRUE(state.command.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.3f, state.command.value[0]);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, -0.2f, state.command.value[7]);
}

void test_invalid_command_fails_closed_to_zero()
{
    auto command = TyrantControl::makeNeutralThrusterCommand(
        2,
        TyrantControl::ThrusterAllocationStatus::SOLVER_FAILED,
        false);
    command.value[3] = 0.9f;

    TyrantActuation::applyMockThrusterCommand(command);

    const auto state = TyrantActuation::getMockThrusterState();
    TEST_ASSERT_FALSE(state.command.valid);
    TEST_ASSERT_FALSE(state.command.enabled);

    for (uint8_t i = 0; i < TyrantControl::THRUSTER_COUNT; ++i)
    {
        TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, state.command.value[i]);
    }
}

void test_disabled_valid_command_is_forced_to_zero()
{
    auto command = TyrantControl::makeNeutralThrusterCommand(
        8,
        TyrantControl::ThrusterAllocationStatus::REQUEST_DISABLED,
        true);
    command.value[1] = 0.7f;

    TyrantActuation::applyMockThrusterCommand(command);

    const auto state = TyrantActuation::getMockThrusterState();
    TEST_ASSERT_TRUE(state.command.valid);
    TEST_ASSERT_FALSE(state.command.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, state.command.value[1]);
}

void test_nonfinite_command_fails_closed()
{
    auto command = TyrantControl::makeNeutralThrusterCommand(
        5,
        TyrantControl::ThrusterAllocationStatus::OK,
        true);
    command.enabled = true;
    command.value[0] = NAN;

    TyrantActuation::applyMockThrusterCommand(command);

    const auto state = TyrantActuation::getMockThrusterState();
    TEST_ASSERT_FALSE(state.command.valid);
    TEST_ASSERT_FALSE(state.command.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, state.command.value[0]);
}

void setup()
{
    delay(2000);
    UNITY_BEGIN();

    RUN_TEST(test_init_is_neutral_and_invalid);
    RUN_TEST(test_valid_enabled_command_is_stored);
    RUN_TEST(test_invalid_command_fails_closed_to_zero);
    RUN_TEST(test_disabled_valid_command_is_forced_to_zero);
    RUN_TEST(test_nonfinite_command_fails_closed);

    UNITY_END();
}

void loop() {}
