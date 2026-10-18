#include <Arduino.h>
#include <unity.h>

#include "sysid/sysid_recorder.h"

namespace
{
TyrantControl::ManualCommand makeCommand()
{
    TyrantControl::ManualCommand command {};
    command.sequence = 7;
    command.surge = 0.25f;
    command.yaw = -0.2f;
    return command;
}

TyrantControl::WrenchRequest makeWrench()
{
    TyrantControl::WrenchRequest request {};
    request.source_sequence = 7;
    request.x = 0.3f;
    request.n = -0.1f;
    request.command_fresh = true;
    request.enabled = true;
    return request;
}


TyrantControl::ThrusterCommand makeThrusterCommand(
    bool valid = true
)
{
    auto command = TyrantControl::makeNeutralThrusterCommand(
        7,
        TyrantControl::ThrusterAllocationStatus::OK,
        valid
    );

    command.enabled = valid;
    command.value[0] = valid ? 0.12f : 0.0f;
    command.value[3] = valid ? -0.08f : 0.0f;
    return command;
}

TyrantSimpleEstimator::State makeState()
{
    TyrantSimpleEstimator::State state {};
    state.roll_rad = 0.1f;
    state.pitch_rad = -0.2f;
    state.yaw_rad = 1.4f;
    state.angular_velocity_b_rad_s = {0.01f, 0.02f, 0.03f};
    state.depth_m = 2.5f;
    state.attitude_valid = true;
    state.heading_valid = true;
    state.depth_valid = true;
    state.status = TyrantSimpleEstimator::Status::RUNNING;
    return state;
}
}

void setUp()
{
    TyrantSysId::init();
}

void tearDown() {}

void test_session_starts_with_ids_and_zero_sequence()
{
    TyrantSysId::startSession(42, 3);
    const auto status = TyrantSysId::getStatus();

    TEST_ASSERT_TRUE(status.active);
    TEST_ASSERT_EQUAL_UINT32(42, status.experiment_id);
    TEST_ASSERT_EQUAL_UINT16(3, status.profile_id);
    TEST_ASSERT_EQUAL_UINT32(0, status.sample_sequence);
}

void test_stop_disables_sampling()
{
    TyrantSysId::startSession(42, 3);
    TyrantSysId::stopSession();

    TEST_ASSERT_FALSE(TyrantSysId::getStatus().active);
    TEST_ASSERT_FALSE(TyrantSysId::sampleDue(100000U));
}

void test_first_sample_is_due_immediately()
{
    TyrantSysId::startSession(1, 0);
    TEST_ASSERT_TRUE(TyrantSysId::sampleDue(1000U));
}

void test_sampling_is_limited_to_20_hz()
{
    TyrantSysId::startSession(1, 0);

    TEST_ASSERT_TRUE(TyrantSysId::sampleDue(100000U));
    TEST_ASSERT_FALSE(TyrantSysId::sampleDue(120000U));
    TEST_ASSERT_TRUE(TyrantSysId::sampleDue(150000U));
}

void test_make_sample_requires_active_session()
{
    TyrantSysId::Sample sample {};
    TyrantSensors::ImuSample imu {};
    TyrantSensors::PressureSample pressure {};

    TEST_ASSERT_FALSE(
        TyrantSysId::makeSample(
            10,
            2,
            true,
            makeCommand(),
            true,
            makeWrench(),
            makeThrusterCommand(false),
            makeState(),
            imu,
            true,
            pressure,
            true,
            sample));
}

void test_make_sample_copies_input_and_output()
{
    TyrantSysId::startSession(99, 5);

    TyrantSensors::ImuSample imu {};
    imu.accel_x = 1.1f;
    imu.gyro_z = 0.04f;

    TyrantSensors::PressureSample pressure {};
    pressure.pressure_pa = 120000.0f;
    pressure.temperature_c = 25.0f;

    TyrantSysId::Sample sample {};

    TEST_ASSERT_TRUE(
        TyrantSysId::makeSample(
            123456,
            2,
            true,
            makeCommand(),
            true,
            makeWrench(),
            makeThrusterCommand(),
            makeState(),
            imu,
            true,
            pressure,
            true,
            sample));

    TEST_ASSERT_EQUAL_UINT32(99, sample.experiment_id);
    TEST_ASSERT_EQUAL_UINT16(5, sample.profile_id);
    TEST_ASSERT_EQUAL_UINT32(1, sample.sample_sequence);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.25f, sample.manual_command.surge);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.3f, sample.requested_wrench.x);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 1.4f, sample.state.yaw_rad);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 1.1f, sample.imu.accel_x);
    TEST_ASSERT_FLOAT_WITHIN(1e-3f, 120000.0f, sample.pressure.pressure_pa);
}

void test_sample_sequence_increments()
{
    TyrantSysId::startSession(10, 1);

    TyrantSensors::ImuSample imu {};
    TyrantSensors::PressureSample pressure {};
    TyrantSysId::Sample first {};
    TyrantSysId::Sample second {};

    TEST_ASSERT_TRUE(TyrantSysId::makeSample(
        1, 1, false, makeCommand(), false, makeWrench(), makeThrusterCommand(false), makeState(),
        imu, false, pressure, false, first));
    TEST_ASSERT_TRUE(TyrantSysId::makeSample(
        2, 1, false, makeCommand(), false, makeWrench(), makeThrusterCommand(false), makeState(),
        imu, false, pressure, false, second));

    TEST_ASSERT_EQUAL_UINT32(1, first.sample_sequence);
    TEST_ASSERT_EQUAL_UINT32(2, second.sample_sequence);
}

void test_thruster_input_copies_backend_command()
{
    TyrantSysId::startSession(10, 1);

    TyrantSensors::ImuSample imu {};
    TyrantSensors::PressureSample pressure {};
    TyrantSysId::Sample sample {};

    TEST_ASSERT_TRUE(TyrantSysId::makeSample(
        1, 2, true, makeCommand(), true, makeWrench(), makeThrusterCommand(), makeState(),
        imu, true, pressure, true, sample));

    TEST_ASSERT_TRUE(sample.thruster_command_valid);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.12f, sample.thruster_command[0]);
    TEST_ASSERT_FLOAT_WITHIN(1e-6f, -0.08f, sample.thruster_command[3]);
}

void setup()
{
    delay(2000);
    UNITY_BEGIN();

    RUN_TEST(test_session_starts_with_ids_and_zero_sequence);
    RUN_TEST(test_stop_disables_sampling);
    RUN_TEST(test_first_sample_is_due_immediately);
    RUN_TEST(test_sampling_is_limited_to_20_hz);
    RUN_TEST(test_make_sample_requires_active_session);
    RUN_TEST(test_make_sample_copies_input_and_output);
    RUN_TEST(test_sample_sequence_increments);
    RUN_TEST(test_thruster_input_copies_backend_command);

    UNITY_END();
}

void loop() {}
