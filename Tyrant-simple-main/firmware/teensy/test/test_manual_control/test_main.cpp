#include <Arduino.h>
#include <math.h>
#include <unity.h>

#include "config/control_config.h"
#include "control/manual_command_manager.h"
#include "control/manual_wrench_mapper.h"
#include "control/stabilized_manual_controller.h"

namespace
{
TyrantControl::ManualCommand makeCommand()
{
    TyrantControl::ManualCommand command {};

    command.sequence = 42;
    command.surge = 0.5f;
    command.sway = -0.25f;
    command.heave = 0.75f;
    command.roll = -0.1f;
    command.pitch = 0.2f;
    command.yaw = -0.6f;

    return command;
}


TyrantControl::ManualCommand makeNeutralCommand()
{
    TyrantControl::ManualCommand command {};
    command.sequence = 100;
    return command;
}


TyrantSimpleEstimator::State makeValidState()
{
    TyrantSimpleEstimator::State state {};

    state.roll_rad = 0.0f;
    state.pitch_rad = 0.0f;
    state.yaw_rad = 1.0f;

    state.angular_velocity_b_rad_s = {
        0.0f,
        0.0f,
        0.0f
    };

    state.depth_m = 2.0f;

    state.attitude_valid = true;
    state.heading_valid = true;
    state.depth_valid = true;
    state.status = TyrantSimpleEstimator::Status::RUNNING;

    return state;
}
}


void setUp()
{
    TyrantControl::initManualCommandManager();

    TyrantControl::initStabilizedManualController(
        TyrantControlConfig::makeDevelopmentStabilizedManualConfig()
    );
}


void tearDown() {}


// ============================================================
// MANUAL COMMAND MANAGER / DIRECT MAPPER REGRESSION
// ============================================================

void test_command_is_not_fresh_before_first_receive()
{
    TyrantControl::ManualCommand command {};

    TEST_ASSERT_FALSE(
        TyrantControl::manualCommandFresh());
    TEST_ASSERT_FALSE(
        TyrantControl::getFreshManualCommand(command));
}


void test_valid_command_is_stored()
{
    const auto input = makeCommand();

    TEST_ASSERT_TRUE(
        TyrantControl::acceptManualCommand(input));

    TyrantControl::ManualCommand output {};
    TEST_ASSERT_TRUE(
        TyrantControl::getFreshManualCommand(output));

    TEST_ASSERT_EQUAL_UINT32(42, output.sequence);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.5f, output.surge);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, -0.25f, output.sway);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, -0.6f, output.yaw);
}


void test_axes_are_clamped_to_normalized_range()
{
    auto input = makeCommand();
    input.surge = 2.0f;
    input.sway = -3.0f;

    TEST_ASSERT_TRUE(
        TyrantControl::acceptManualCommand(input));

    TyrantControl::ManualCommand output {};
    TEST_ASSERT_TRUE(
        TyrantControl::getFreshManualCommand(output));

    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 1.0f, output.surge);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, -1.0f, output.sway);
}


void test_nonfinite_command_is_rejected()
{
    TEST_ASSERT_TRUE(
        TyrantControl::acceptManualCommand(makeCommand()));

    auto input = makeCommand();
    input.yaw = NAN;

    TEST_ASSERT_FALSE(
        TyrantControl::acceptManualCommand(input));

    TEST_ASSERT_FALSE(
        TyrantControl::manualCommandFresh());
}


void test_command_becomes_stale()
{
    TEST_ASSERT_TRUE(
        TyrantControl::acceptManualCommand(makeCommand()));

    delay(275);

    TEST_ASSERT_FALSE(
        TyrantControl::manualCommandFresh());
}


void test_mapper_passes_axes_when_enabled()
{
    const auto command = makeCommand();

    const auto request =
        TyrantControl::makeManualWrenchRequest(
            command,
            true,
            true);

    TEST_ASSERT_TRUE(request.enabled);
    TEST_ASSERT_TRUE(request.command_fresh);
    TEST_ASSERT_EQUAL_UINT32(42, request.source_sequence);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, command.surge, request.x);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, command.sway, request.y);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, command.heave, request.z);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, command.roll, request.k);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, command.pitch, request.m);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, command.yaw, request.n);
}


void test_mapper_outputs_zero_when_propulsion_blocked()
{
    const auto request =
        TyrantControl::makeManualWrenchRequest(
            makeCommand(),
            true,
            false);

    TEST_ASSERT_FALSE(request.enabled);
    TEST_ASSERT_TRUE(request.command_fresh);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.x);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.n);
}


void test_mapper_outputs_zero_when_command_stale()
{
    const auto request =
        TyrantControl::makeManualWrenchRequest(
            makeCommand(),
            false,
            true);

    TEST_ASSERT_FALSE(request.enabled);
    TEST_ASSERT_FALSE(request.command_fresh);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.x);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.n);
}


// ============================================================
// STABILIZED MANUAL CONTROLLER
// ============================================================

void test_stabilized_controller_passes_surge_and_sway()
{
    auto command = makeNeutralCommand();
    command.surge = 0.4f;
    command.sway = -0.3f;

    const auto request =
        TyrantControl::updateStabilizedManualController(
            command,
            makeValidState(),
            true,
            true,
            0.02f);

    TEST_ASSERT_TRUE(request.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.4f, request.x);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, -0.3f, request.y);
}


void test_depth_stick_slews_reference_downward()
{
    auto command = makeNeutralCommand();
    command.heave = 1.0f;

    const auto request =
        TyrantControl::updateStabilizedManualController(
            command,
            makeValidState(),
            true,
            true,
            0.10f);

    TEST_ASSERT_TRUE(request.enabled);
    TEST_ASSERT_TRUE(request.z > 0.0f);
}


void test_depth_hold_corrects_back_to_latched_depth()
{
    const auto command = makeNeutralCommand();
    auto state = makeValidState();

    (void)TyrantControl::updateStabilizedManualController(
        command,
        state,
        true,
        true,
        0.02f);

    state.depth_m = 1.8f;

    const auto request =
        TyrantControl::updateStabilizedManualController(
            command,
            state,
            true,
            true,
            0.02f);

    TEST_ASSERT_TRUE(request.z > 0.0f);
}


void test_small_heave_inside_deadzone_does_not_move_reference()
{
    auto command = makeNeutralCommand();
    command.heave = 0.02f;

    const auto request =
        TyrantControl::updateStabilizedManualController(
            command,
            makeValidState(),
            true,
            true,
            0.10f);

    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.z);
}


void test_roll_and_pitch_pd_correct_toward_zero_reference()
{
    auto state = makeValidState();
    state.roll_rad = 0.10f;
    state.pitch_rad = -0.10f;

    const auto request =
        TyrantControl::updateStabilizedManualController(
            makeNeutralCommand(),
            state,
            true,
            true,
            0.02f);

    TEST_ASSERT_TRUE(request.k < 0.0f);
    TEST_ASSERT_TRUE(request.m > 0.0f);
}


void test_yaw_stick_slews_heading_reference()
{
    auto command = makeNeutralCommand();
    command.yaw = 1.0f;

    const auto request =
        TyrantControl::updateStabilizedManualController(
            command,
            makeValidState(),
            true,
            true,
            0.10f);

    TEST_ASSERT_TRUE(request.n > 0.0f);
}


void test_yaw_reference_wrap_uses_short_angle_error()
{
    auto command = makeNeutralCommand();
    command.yaw = 1.0f;

    auto state = makeValidState();
    state.yaw_rad = 3.13f;

    const auto first =
        TyrantControl::updateStabilizedManualController(
            command,
            state,
            true,
            true,
            0.10f);

    TEST_ASSERT_TRUE(first.n > 0.0f);
    TEST_ASSERT_TRUE(first.n < 0.5f);

    command.yaw = 0.0f;
    state.yaw_rad = -3.13f;

    const auto second =
        TyrantControl::updateStabilizedManualController(
            command,
            state,
            true,
            true,
            0.02f);

    TEST_ASSERT_TRUE(second.n > -0.5f);
    TEST_ASSERT_TRUE(second.n < 0.5f);
}


void test_invalid_depth_disables_only_depth_axis()
{
    auto command = makeNeutralCommand();
    command.surge = 0.5f;
    command.heave = 1.0f;

    auto state = makeValidState();
    state.depth_valid = false;

    const auto request =
        TyrantControl::updateStabilizedManualController(
            command,
            state,
            true,
            true,
            0.02f);

    TEST_ASSERT_TRUE(request.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.5f, request.x);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.z);
}


void test_invalid_heading_disables_only_yaw_axis()
{
    auto command = makeNeutralCommand();
    command.surge = 0.5f;
    command.yaw = 1.0f;

    auto state = makeValidState();
    state.heading_valid = false;

    const auto request =
        TyrantControl::updateStabilizedManualController(
            command,
            state,
            true,
            true,
            0.02f);

    TEST_ASSERT_TRUE(request.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.5f, request.x);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.n);
}


void test_invalid_attitude_zeroes_entire_request()
{
    auto state = makeValidState();
    state.attitude_valid = false;

    const auto request =
        TyrantControl::updateStabilizedManualController(
            makeCommand(),
            state,
            true,
            true,
            0.02f);

    TEST_ASSERT_FALSE(request.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.x);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.k);
}


void test_stale_command_resets_held_references()
{
    auto command = makeNeutralCommand();
    command.heave = 1.0f;

    auto state = makeValidState();

    (void)TyrantControl::updateStabilizedManualController(
        command,
        state,
        true,
        true,
        0.10f);

    const auto stale =
        TyrantControl::updateStabilizedManualController(
            command,
            state,
            false,
            true,
            0.02f);

    TEST_ASSERT_FALSE(stale.enabled);

    command.heave = 0.0f;
    state.depth_m = 3.0f;

    const auto resumed =
        TyrantControl::updateStabilizedManualController(
            command,
            state,
            true,
            true,
            0.02f);

    TEST_ASSERT_TRUE(resumed.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, resumed.z);
}


void test_long_control_gap_zeroes_and_resets_controller()
{
    const auto request =
        TyrantControl::updateStabilizedManualController(
            makeCommand(),
            makeValidState(),
            true,
            true,
            0.20f);

    TEST_ASSERT_FALSE(request.enabled);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.x);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f, request.n);
}


void setup()
{
    delay(500);

    UNITY_BEGIN();

    RUN_TEST(test_command_is_not_fresh_before_first_receive);
    RUN_TEST(test_valid_command_is_stored);
    RUN_TEST(test_axes_are_clamped_to_normalized_range);
    RUN_TEST(test_nonfinite_command_is_rejected);
    RUN_TEST(test_command_becomes_stale);
    RUN_TEST(test_mapper_passes_axes_when_enabled);
    RUN_TEST(test_mapper_outputs_zero_when_propulsion_blocked);
    RUN_TEST(test_mapper_outputs_zero_when_command_stale);

    RUN_TEST(test_stabilized_controller_passes_surge_and_sway);
    RUN_TEST(test_depth_stick_slews_reference_downward);
    RUN_TEST(test_depth_hold_corrects_back_to_latched_depth);
    RUN_TEST(test_small_heave_inside_deadzone_does_not_move_reference);
    RUN_TEST(test_roll_and_pitch_pd_correct_toward_zero_reference);
    RUN_TEST(test_yaw_stick_slews_heading_reference);
    RUN_TEST(test_yaw_reference_wrap_uses_short_angle_error);
    RUN_TEST(test_invalid_depth_disables_only_depth_axis);
    RUN_TEST(test_invalid_heading_disables_only_yaw_axis);
    RUN_TEST(test_invalid_attitude_zeroes_entire_request);
    RUN_TEST(test_stale_command_resets_held_references);
    RUN_TEST(test_long_control_gap_zeroes_and_resets_controller);

    UNITY_END();
}


void loop() {}
