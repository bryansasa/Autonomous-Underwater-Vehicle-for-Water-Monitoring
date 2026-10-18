#include <Arduino.h>
#include <unity.h>

#include "safety/safety_manager.h"
#include "vehicle/vehicle_mode.h"

namespace
{
void makeCommunicationHealthy()
{
    TyrantSafety::setTransportConnected(true);
    TyrantSafety::notifyHostHeartbeat();
}
}

void setUp()
{
    TyrantSafety::init();
}

void tearDown() {}

void test_init_enters_idle_with_propulsion_blocked()
{
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Mode::IDLE),
        TyrantSafety::getMode());
    TEST_ASSERT_FALSE(TyrantSafety::communicationHealthy());
    TEST_ASSERT_FALSE(TyrantSafety::propulsionAllowed());
}

void test_manual_rejected_until_communication_healthy()
{
    auto result = TyrantSafety::requestMode(
        static_cast<uint8_t>(TyrantVehicle::Mode::MANUAL));

    TEST_ASSERT_FALSE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Reason::SYSTEM_UNHEALTHY),
        result.reason);

    makeCommunicationHealthy();

    result = TyrantSafety::requestMode(
        static_cast<uint8_t>(TyrantVehicle::Mode::MANUAL));

    TEST_ASSERT_TRUE(result.accepted);
    TEST_ASSERT_TRUE(TyrantSafety::propulsionAllowed());
}

void test_auto_is_blocked_until_autonomy_ready()
{
    makeCommunicationHealthy();

    const auto result = TyrantSafety::requestMode(
        static_cast<uint8_t>(TyrantVehicle::Mode::AUTO));

    TEST_ASSERT_FALSE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Reason::AUTONOMY_NOT_READY),
        result.reason);
    TEST_ASSERT_FALSE(TyrantSafety::autonomyReady());
}

void test_auto_allowed_after_explicit_autonomy_ready_signal()
{
    makeCommunicationHealthy();
    TyrantSafety::setAutonomyReady(true);

    TEST_ASSERT_TRUE(TyrantSafety::autonomyReady());

    const auto result = TyrantSafety::requestMode(
        static_cast<uint8_t>(TyrantVehicle::Mode::AUTO));

    TEST_ASSERT_TRUE(result.accepted);
    TEST_ASSERT_TRUE(TyrantSafety::propulsionAllowed());
}

void test_emergency_actuation_authority_is_separate_from_normal_propulsion()
{
    TyrantSafety::triggerEmergency();

    TEST_ASSERT_FALSE(TyrantSafety::propulsionAllowed());
    TEST_ASSERT_TRUE(TyrantSafety::emergencyActuationAllowed());
}

void test_disconnect_forces_manual_to_safe()
{
    makeCommunicationHealthy();
    const auto result = TyrantSafety::requestMode(
        static_cast<uint8_t>(TyrantVehicle::Mode::MANUAL));
    TEST_ASSERT_TRUE(result.accepted);

    TyrantSafety::setTransportConnected(false);

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Mode::SAFE),
        TyrantSafety::getMode());
    TEST_ASSERT_FALSE(TyrantSafety::propulsionAllowed());

    uint8_t reason = 0;
    TEST_ASSERT_TRUE(TyrantSafety::takeInternalModeEvent(reason));
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Reason::COMMUNICATION_TIMEOUT),
        reason);
    TEST_ASSERT_FALSE(TyrantSafety::takeInternalModeEvent(reason));
}

void test_heartbeat_timeout_forces_safe()
{
    makeCommunicationHealthy();
    const auto result = TyrantSafety::requestMode(
        static_cast<uint8_t>(TyrantVehicle::Mode::MANUAL));
    TEST_ASSERT_TRUE(result.accepted);

    delay(550);
    TyrantSafety::update();

    TEST_ASSERT_FALSE(TyrantSafety::communicationHealthy());
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Mode::SAFE),
        TyrantSafety::getMode());
}

void test_invalid_mode_is_rejected()
{
    const auto result = TyrantSafety::requestMode(255);
    TEST_ASSERT_FALSE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Reason::INVALID_MODE),
        result.reason);
}

void setup()
{
    delay(500);
    UNITY_BEGIN();
    RUN_TEST(test_init_enters_idle_with_propulsion_blocked);
    RUN_TEST(test_manual_rejected_until_communication_healthy);
    RUN_TEST(test_auto_is_blocked_until_autonomy_ready);
    RUN_TEST(test_auto_allowed_after_explicit_autonomy_ready_signal);
    RUN_TEST(test_emergency_actuation_authority_is_separate_from_normal_propulsion);
    RUN_TEST(test_disconnect_forces_manual_to_safe);
    RUN_TEST(test_heartbeat_timeout_forces_safe);
    RUN_TEST(test_invalid_mode_is_rejected);
    UNITY_END();
}

void loop() {}
