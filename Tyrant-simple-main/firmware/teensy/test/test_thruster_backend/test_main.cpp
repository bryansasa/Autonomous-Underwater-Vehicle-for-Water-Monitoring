#include <Arduino.h>
#include <unity.h>

#include "actuation/thruster_backend.h"

namespace
{
TyrantActuation::ThrusterBackendConfig makeConfig()
{
    TyrantActuation::ThrusterBackendConfig config {};
    config.command_timeout_us = 100000u;

    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        config.pwm.pin[index] = 0xFFu;
        config.pwm.channel[index] = {
            1100u,
            1500u,
            1900u,
            0.05f,
            false
        };
    }

    return config;
}

TyrantControl::ThrusterCommand enabledCommand()
{
    auto command =
        TyrantControl::makeNeutralThrusterCommand(
            42,
            TyrantControl::ThrusterAllocationStatus::OK,
            true
        );

    command.enabled = true;
    command.value[0] = 0.5f;
    return command;
}

void setUpBackend()
{
    TyrantActuation::initThrusterBackend(
        makeConfig(),
        1000u
    );
}

void test_mock_backend_is_ready()
{
    setUpBackend();
    const auto status =
        TyrantActuation::getThrusterBackendStatus(1000u);

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantActuation::ThrusterBackendType::MOCK),
        static_cast<uint8_t>(status.type)
    );
    TEST_ASSERT_TRUE(status.ready);
    TEST_ASSERT_FALSE(status.physical_output_enabled);
}

void test_valid_command_is_applied()
{
    setUpBackend();
    const auto command = enabledCommand();

    TyrantActuation::applyThrusterBackendCommand(
        command,
        2000u
    );

    const auto status =
        TyrantActuation::getThrusterBackendStatus(2000u);

    TEST_ASSERT_TRUE(status.applied_command.valid);
    TEST_ASSERT_TRUE(status.applied_command.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1.0e-6f, 0.5f, status.applied_command.value[0]);
    TEST_ASSERT_EQUAL_UINT32(1u, status.apply_count);
}

void test_disabled_command_becomes_neutral()
{
    setUpBackend();
    auto command = enabledCommand();
    command.enabled = false;
    command.value[0] = 0.9f;

    TyrantActuation::applyThrusterBackendCommand(
        command,
        2000u
    );

    const auto status =
        TyrantActuation::getThrusterBackendStatus(2000u);

    TEST_ASSERT_FALSE(status.applied_command.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1.0e-6f, 0.0f, status.applied_command.value[0]);
}

void test_invalid_command_latches_fault()
{
    setUpBackend();
    auto command = enabledCommand();
    command.valid = false;

    TyrantActuation::applyThrusterBackendCommand(
        command,
        2000u
    );

    const auto status =
        TyrantActuation::getThrusterBackendStatus(2000u);

    TEST_ASSERT_TRUE(status.fault_latched);
    TEST_ASSERT_FALSE(status.ready);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantActuation::ThrusterBackendFault::INVALID_COMMAND),
        static_cast<uint8_t>(status.fault)
    );
    TEST_ASSERT_EQUAL_UINT32(1u, status.reject_count);
}

void test_enabled_command_timeout_neutralizes_and_faults()
{
    setUpBackend();
    const auto command = enabledCommand();

    TyrantActuation::applyThrusterBackendCommand(
        command,
        2000u
    );

    TyrantActuation::updateThrusterBackend(103001u);

    const auto status =
        TyrantActuation::getThrusterBackendStatus(103001u);

    TEST_ASSERT_TRUE(status.fault_latched);
    TEST_ASSERT_FALSE(status.applied_command.enabled);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantActuation::ThrusterBackendFault::COMMAND_TIMEOUT),
        static_cast<uint8_t>(status.fault)
    );
}

void test_disabled_command_does_not_trigger_watchdog()
{
    setUpBackend();
    auto command = enabledCommand();
    command.enabled = false;

    TyrantActuation::applyThrusterBackendCommand(
        command,
        2000u
    );

    TyrantActuation::updateThrusterBackend(500000u);

    const auto status =
        TyrantActuation::getThrusterBackendStatus(500000u);

    TEST_ASSERT_FALSE(status.fault_latched);
    TEST_ASSERT_TRUE(status.ready);
}
}

void setup()
{
    delay(2000);
    UNITY_BEGIN();
    RUN_TEST(test_mock_backend_is_ready);
    RUN_TEST(test_valid_command_is_applied);
    RUN_TEST(test_disabled_command_becomes_neutral);
    RUN_TEST(test_invalid_command_latches_fault);
    RUN_TEST(test_enabled_command_timeout_neutralizes_and_faults);
    RUN_TEST(test_disabled_command_does_not_trigger_watchdog);
    UNITY_END();
}

void loop() {}
