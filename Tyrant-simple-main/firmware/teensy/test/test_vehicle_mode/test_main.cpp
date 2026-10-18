#include <Arduino.h>
#include <unity.h>

#include "vehicle/vehicle_mode.h"

void setUp()
{
    TyrantVehicle::init();
}

void tearDown() {}

void test_init_starts_in_boot()
{
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Mode::BOOT),
        static_cast<uint8_t>(TyrantVehicle::getMode()));
}

void test_successful_boot_enters_idle()
{
    TyrantVehicle::completeBoot(true);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Mode::IDLE),
        static_cast<uint8_t>(TyrantVehicle::getMode()));
}

void test_failed_boot_latches_fault()
{
    TyrantVehicle::completeBoot(false);
    const auto result = TyrantVehicle::requestMode(
        TyrantVehicle::Mode::IDLE,
        true,
        true);

    TEST_ASSERT_FALSE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Reason::FAULT_LATCHED),
        static_cast<uint8_t>(result.reason));
}

void test_manual_requires_healthy_system()
{
    TyrantVehicle::completeBoot(true);

    auto result = TyrantVehicle::requestMode(
        TyrantVehicle::Mode::MANUAL,
        false,
        false);

    TEST_ASSERT_FALSE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Reason::SYSTEM_UNHEALTHY),
        static_cast<uint8_t>(result.reason));

    result = TyrantVehicle::requestMode(
        TyrantVehicle::Mode::MANUAL,
        true,
        false);

    TEST_ASSERT_TRUE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Mode::MANUAL),
        static_cast<uint8_t>(TyrantVehicle::getMode()));
}

void test_auto_requires_autonomy_ready()
{
    TyrantVehicle::completeBoot(true);

    auto result = TyrantVehicle::requestMode(
        TyrantVehicle::Mode::AUTO,
        true,
        false);

    TEST_ASSERT_FALSE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Reason::AUTONOMY_NOT_READY),
        static_cast<uint8_t>(result.reason));

    result = TyrantVehicle::requestMode(
        TyrantVehicle::Mode::AUTO,
        true,
        true);

    TEST_ASSERT_TRUE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Mode::AUTO),
        static_cast<uint8_t>(TyrantVehicle::getMode()));
}

void test_safe_can_be_requested_and_recovers_through_idle()
{
    TyrantVehicle::completeBoot(true);

    auto result = TyrantVehicle::requestMode(
        TyrantVehicle::Mode::SAFE,
        false,
        false);

    TEST_ASSERT_TRUE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Mode::SAFE),
        static_cast<uint8_t>(TyrantVehicle::getMode()));

    result = TyrantVehicle::requestMode(
        TyrantVehicle::Mode::IDLE,
        true,
        false);

    TEST_ASSERT_TRUE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Mode::IDLE),
        static_cast<uint8_t>(TyrantVehicle::getMode()));
}

void test_emergency_is_latched()
{
    TyrantVehicle::completeBoot(true);
    TyrantVehicle::forceEmergency();

    const auto result = TyrantVehicle::requestMode(
        TyrantVehicle::Mode::IDLE,
        true,
        true);

    TEST_ASSERT_FALSE(result.accepted);
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantVehicle::Reason::EMERGENCY_LATCHED),
        static_cast<uint8_t>(result.reason));
}

void setup()
{
    delay(500);
    UNITY_BEGIN();
    RUN_TEST(test_init_starts_in_boot);
    RUN_TEST(test_successful_boot_enters_idle);
    RUN_TEST(test_failed_boot_latches_fault);
    RUN_TEST(test_manual_requires_healthy_system);
    RUN_TEST(test_auto_requires_autonomy_ready);
    RUN_TEST(test_safe_can_be_requested_and_recovers_through_idle);
    RUN_TEST(test_emergency_is_latched);
    UNITY_END();
}

void loop() {}
