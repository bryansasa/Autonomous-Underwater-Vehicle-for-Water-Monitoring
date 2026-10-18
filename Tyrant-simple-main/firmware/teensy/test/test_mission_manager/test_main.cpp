#include <Arduino.h>
#include <unity.h>

#include "application/mission_manager.h"

namespace
{
TyrantSimpleEstimator::State validState()
{
    TyrantSimpleEstimator::State state {};
    state.roll_rad = 0.0f;
    state.pitch_rad = 0.0f;
    state.yaw_rad = 0.0f;
    state.depth_m = 1.0f;
    state.attitude_valid = true;
    state.heading_valid = true;
    state.depth_valid = true;
    state.status = TyrantSimpleEstimator::Status::RUNNING;
    return state;
}
}

void setUp()
{
    TyrantMission::init();
}

void tearDown() {}

void test_empty_mission_is_not_ready_and_cannot_start()
{
    TEST_ASSERT_FALSE(TyrantMission::readyForAuto());
    TEST_ASSERT_FALSE(TyrantMission::start(100));
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantMission::Reason::NO_STEPS),
        static_cast<uint8_t>(TyrantMission::getStatus().reason));
}

void test_append_valid_step_makes_mission_ready()
{
    TyrantMission::Step step {};
    step.type = TyrantMission::StepType::WAIT;
    step.duration_ms = 1000;

    TEST_ASSERT_TRUE(TyrantMission::appendStep(step));
    TEST_ASSERT_TRUE(TyrantMission::readyForAuto());
    TEST_ASSERT_EQUAL_UINT8(1, TyrantMission::getStatus().step_count);
}

void test_invalid_step_is_rejected()
{
    TyrantMission::Step step {};
    step.type = TyrantMission::StepType::SURGE_TIME;
    step.effort = 0.5f;
    step.duration_ms = 0;

    TEST_ASSERT_FALSE(TyrantMission::appendStep(step));
}

void test_surge_time_generates_surge_command_then_completes()
{
    TyrantMission::Step step {};
    step.type = TyrantMission::StepType::SURGE_TIME;
    step.effort = 0.4f;
    step.duration_ms = 1000;
    TEST_ASSERT_TRUE(TyrantMission::appendStep(step));
    TEST_ASSERT_TRUE(TyrantMission::start(100));

    TyrantControl::ManualCommand command {};
    auto state = validState();

    TEST_ASSERT_TRUE(TyrantMission::update(state, 500, command));
    TEST_ASSERT_FLOAT_WITHIN(1.0e-6f, 0.4f, command.surge);

    TEST_ASSERT_FALSE(TyrantMission::update(state, 1100, command));
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantMission::State::COMPLETE),
        static_cast<uint8_t>(TyrantMission::getStatus().state));
}

void test_dive_step_commands_positive_heave()
{
    TyrantMission::Step step {};
    step.type = TyrantMission::StepType::DIVE_TO_DEPTH;
    step.target = 2.0f;
    step.effort = 0.5f;
    step.tolerance = 0.05f;
    TEST_ASSERT_TRUE(TyrantMission::appendStep(step));
    TEST_ASSERT_TRUE(TyrantMission::start(0));

    auto state = validState();
    TyrantControl::ManualCommand command {};
    TEST_ASSERT_TRUE(TyrantMission::update(state, 20, command));
    TEST_ASSERT_FLOAT_WITHIN(1.0e-6f, 0.5f, command.heave);
}

void test_surface_step_commands_negative_heave()
{
    TyrantMission::Step step {};
    step.type = TyrantMission::StepType::SURFACE_TO_DEPTH;
    step.target = 0.2f;
    step.effort = 0.6f;
    step.tolerance = 0.05f;
    TEST_ASSERT_TRUE(TyrantMission::appendStep(step));
    TEST_ASSERT_TRUE(TyrantMission::start(0));

    auto state = validState();
    state.depth_m = 1.5f;
    TyrantControl::ManualCommand command {};
    TEST_ASSERT_TRUE(TyrantMission::update(state, 20, command));
    TEST_ASSERT_FLOAT_WITHIN(1.0e-6f, -0.6f, command.heave);
}

void test_depth_step_completes_inside_tolerance()
{
    TyrantMission::Step step {};
    step.type = TyrantMission::StepType::DIVE_TO_DEPTH;
    step.target = 1.0f;
    step.effort = 0.4f;
    step.tolerance = 0.1f;
    TEST_ASSERT_TRUE(TyrantMission::appendStep(step));
    TEST_ASSERT_TRUE(TyrantMission::start(0));

    auto state = validState();
    state.depth_m = 1.04f;
    TyrantControl::ManualCommand command {};
    TEST_ASSERT_FALSE(TyrantMission::update(state, 20, command));
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantMission::State::COMPLETE),
        static_cast<uint8_t>(TyrantMission::getStatus().state));
}

void test_turn_uses_short_wrapped_direction()
{
    TyrantMission::Step step {};
    step.type = TyrantMission::StepType::TURN_TO_HEADING;
    step.target = -3.10f;
    step.effort = 0.3f;
    step.tolerance = 0.01f;
    TEST_ASSERT_TRUE(TyrantMission::appendStep(step));
    TEST_ASSERT_TRUE(TyrantMission::start(0));

    auto state = validState();
    state.yaw_rad = 3.10f;
    TyrantControl::ManualCommand command {};
    TEST_ASSERT_TRUE(TyrantMission::update(state, 20, command));
    TEST_ASSERT_TRUE(command.yaw > 0.0f);
}

void test_required_state_loss_fails_depth_step()
{
    TyrantMission::Step step {};
    step.type = TyrantMission::StepType::DIVE_TO_DEPTH;
    step.target = 2.0f;
    step.effort = 0.5f;
    step.tolerance = 0.05f;
    TEST_ASSERT_TRUE(TyrantMission::appendStep(step));
    TEST_ASSERT_TRUE(TyrantMission::start(0));

    auto state = validState();
    state.depth_valid = false;
    TyrantControl::ManualCommand command {};
    TEST_ASSERT_FALSE(TyrantMission::update(state, 20, command));
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantMission::State::FAILED),
        static_cast<uint8_t>(TyrantMission::getStatus().state));
}

void test_wait_then_second_step_advances_sequence()
{
    TyrantMission::Step wait {};
    wait.type = TyrantMission::StepType::WAIT;
    wait.duration_ms = 100;
    TEST_ASSERT_TRUE(TyrantMission::appendStep(wait));

    TyrantMission::Step surge {};
    surge.type = TyrantMission::StepType::SURGE_TIME;
    surge.effort = 0.2f;
    surge.duration_ms = 100;
    TEST_ASSERT_TRUE(TyrantMission::appendStep(surge));

    TEST_ASSERT_TRUE(TyrantMission::start(0));
    auto state = validState();
    TyrantControl::ManualCommand command {};

    TEST_ASSERT_TRUE(TyrantMission::update(state, 100, command));
    TEST_ASSERT_EQUAL_UINT8(1, TyrantMission::getStatus().current_step);

    TEST_ASSERT_TRUE(TyrantMission::update(state, 120, command));
    TEST_ASSERT_FLOAT_WITHIN(1.0e-6f, 0.2f, command.surge);
}

void setup()
{
    delay(500);
    UNITY_BEGIN();
    RUN_TEST(test_empty_mission_is_not_ready_and_cannot_start);
    RUN_TEST(test_append_valid_step_makes_mission_ready);
    RUN_TEST(test_invalid_step_is_rejected);
    RUN_TEST(test_surge_time_generates_surge_command_then_completes);
    RUN_TEST(test_dive_step_commands_positive_heave);
    RUN_TEST(test_surface_step_commands_negative_heave);
    RUN_TEST(test_depth_step_completes_inside_tolerance);
    RUN_TEST(test_turn_uses_short_wrapped_direction);
    RUN_TEST(test_required_state_loss_fails_depth_step);
    RUN_TEST(test_wait_then_second_step_advances_sequence);
    UNITY_END();
}

void loop() {}
