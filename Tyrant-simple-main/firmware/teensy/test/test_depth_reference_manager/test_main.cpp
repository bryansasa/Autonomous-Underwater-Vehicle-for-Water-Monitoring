#include <Arduino.h>
#include <unity.h>

#include "application/depth_reference_manager.h"
#include "mock_pressure_source.h"
#include "safety/safety_manager.h"
#include "sensors/sensor_manager.h"
#include "vehicle/vehicle_mode.h"

namespace
{
MockPressureSource mock_pressure;
constexpr uint8_t SET_SURFACE = 1;
constexpr uint8_t CLEAR_REFERENCE = 2;

void bindReadyPressure()
{
    TyrantSensors::setPressureSource(mock_pressure);
    TyrantSensors::init();
    TyrantSensors::update();
}
}

void test_invalid_command_rejected()
{
    TyrantSafety::init();
    const auto result = TyrantDepthReference::handleRequest(99);
    TEST_ASSERT_FALSE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantDepthReference::Reason::INVALID_COMMAND),
        static_cast<uint8_t>(result.reason));
}

void test_set_surface_requires_ready_pressure()
{
    TyrantSafety::init();
    TyrantSensors::init();

    const auto result = TyrantDepthReference::handleRequest(SET_SURFACE);
    TEST_ASSERT_FALSE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantDepthReference::Reason::PRESSURE_NOT_READY),
        static_cast<uint8_t>(result.reason));
}

void test_set_and_clear_surface_reference()
{
    TyrantSafety::init();
    bindReadyPressure();

    auto result = TyrantDepthReference::handleRequest(SET_SURFACE);
    TEST_ASSERT_TRUE(result.accepted);
    TEST_ASSERT_TRUE(result.reference_valid);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 101325.0f, result.surface_pressure_pa);

    result = TyrantDepthReference::handleRequest(CLEAR_REFERENCE);
    TEST_ASSERT_TRUE(result.accepted);
    TEST_ASSERT_FALSE(result.reference_valid);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, result.surface_pressure_pa);
}

void test_reference_change_rejected_outside_idle()
{
    TyrantSafety::init();
    bindReadyPressure();

    TyrantSafety::setTransportConnected(true);
    TyrantSafety::notifyHostHeartbeat();
    const auto mode_result = TyrantSafety::requestMode(
        static_cast<uint8_t>(TyrantVehicle::Mode::MANUAL));
    TEST_ASSERT_TRUE(mode_result.accepted);

    const auto result = TyrantDepthReference::handleRequest(SET_SURFACE);
    TEST_ASSERT_FALSE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantDepthReference::Reason::VEHICLE_NOT_IDLE),
        static_cast<uint8_t>(result.reason));
}

void setup()
{
    delay(500);
    UNITY_BEGIN();
    // This must run before a pressure source is bound in this test binary.
    RUN_TEST(test_invalid_command_rejected);
    RUN_TEST(test_set_surface_requires_ready_pressure);
    RUN_TEST(test_set_and_clear_surface_reference);
    RUN_TEST(test_reference_change_rejected_outside_idle);
    UNITY_END();
}

void loop() {}
