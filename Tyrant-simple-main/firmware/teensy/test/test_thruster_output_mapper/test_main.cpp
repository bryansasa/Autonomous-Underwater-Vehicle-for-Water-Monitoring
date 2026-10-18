#include <Arduino.h>
#include <unity.h>

#include "actuation/thruster_output_mapper.h"

namespace
{
TyrantActuation::PwmChannelConfig config()
{
    return {
        1100u,
        1500u,
        1900u,
        0.05f,
        false
    };
}

void test_neutral_maps_to_neutral_pulse()
{
    TEST_ASSERT_EQUAL_UINT16(
        1500u,
        TyrantActuation::mapNormalizedCommandToPulse(
            0.0f,
            config()
        )
    );
}

void test_full_forward_maps_to_forward_pulse()
{
    TEST_ASSERT_EQUAL_UINT16(
        1900u,
        TyrantActuation::mapNormalizedCommandToPulse(
            1.0f,
            config()
        )
    );
}

void test_full_reverse_maps_to_reverse_pulse()
{
    TEST_ASSERT_EQUAL_UINT16(
        1100u,
        TyrantActuation::mapNormalizedCommandToPulse(
            -1.0f,
            config()
        )
    );
}

void test_deadband_maps_to_neutral()
{
    TEST_ASSERT_EQUAL_UINT16(
        1500u,
        TyrantActuation::mapNormalizedCommandToPulse(
            0.04f,
            config()
        )
    );
}

void test_inversion_swaps_direction()
{
    auto inverted = config();
    inverted.inverted = true;

    TEST_ASSERT_EQUAL_UINT16(
        1100u,
        TyrantActuation::mapNormalizedCommandToPulse(
            1.0f,
            inverted
        )
    );
}

void test_disabled_command_produces_all_neutral()
{
    TyrantControl::ThrusterCommand command =
        TyrantControl::makeNeutralThrusterCommand(
            1,
            TyrantControl::ThrusterAllocationStatus::OK,
            true
        );

    command.enabled = false;
    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        command.value[index] = 1.0f;
    }

    TyrantActuation::PwmChannelConfig channels[TyrantControl::THRUSTER_COUNT] {};
    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        channels[index] = config();
    }

    const auto frame =
        TyrantActuation::mapThrusterCommandToPwm(
            command,
            channels
        );

    TEST_ASSERT_TRUE(frame.valid);
    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        TEST_ASSERT_EQUAL_UINT16(1500u, frame.pulse_us[index]);
    }
}

void test_invalid_channel_marks_frame_invalid()
{
    TyrantControl::ThrusterCommand command =
        TyrantControl::makeNeutralThrusterCommand(
            1,
            TyrantControl::ThrusterAllocationStatus::OK,
            true
        );

    TyrantActuation::PwmChannelConfig channels[TyrantControl::THRUSTER_COUNT] {};
    for (uint8_t index = 0; index < TyrantControl::THRUSTER_COUNT; ++index)
    {
        channels[index] = config();
    }
    channels[3].neutral_us = channels[3].reverse_us;

    const auto frame =
        TyrantActuation::mapThrusterCommandToPwm(
            command,
            channels
        );

    TEST_ASSERT_FALSE(frame.valid);
}
}

void setup()
{
    delay(2000);
    UNITY_BEGIN();
    RUN_TEST(test_neutral_maps_to_neutral_pulse);
    RUN_TEST(test_full_forward_maps_to_forward_pulse);
    RUN_TEST(test_full_reverse_maps_to_reverse_pulse);
    RUN_TEST(test_deadband_maps_to_neutral);
    RUN_TEST(test_inversion_swaps_direction);
    RUN_TEST(test_disabled_command_produces_all_neutral);
    RUN_TEST(test_invalid_channel_marks_frame_invalid);
    UNITY_END();
}

void loop() {}
