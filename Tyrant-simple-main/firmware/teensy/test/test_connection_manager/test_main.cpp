#include <Arduino.h>
#include <unity.h>

#include "communication/connection_manager.h"
#include "communication/ros_interface.h"
#include "safety/safety_manager.h"

namespace
{
bool ping_result = false;
bool create_result = true;
uint32_t ping_calls = 0;
uint32_t create_calls = 0;
uint32_t destroy_calls = 0;
uint32_t spin_calls = 0;
}

namespace TyrantROS
{
bool pingAgent(uint32_t, uint8_t)
{
    ++ping_calls;
    return ping_result;
}

bool createEntities()
{
    ++create_calls;
    return create_result;
}

void destroyEntities()
{
    ++destroy_calls;
}

void spin()
{
    ++spin_calls;
}
}

void setUp()
{
    ping_result = false;
    create_result = true;
    ping_calls = 0;
    create_calls = 0;
    destroy_calls = 0;
    spin_calls = 0;
    TyrantSafety::init();
    TyrantConnection::init();
}

void tearDown() {}

void test_starts_waiting_for_agent()
{
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantConnection::State::WAITING_AGENT),
        static_cast<uint8_t>(TyrantConnection::getState()));
    TEST_ASSERT_FALSE(TyrantConnection::connected());
    TEST_ASSERT_FALSE(TyrantSafety::transportConnected());
}

void test_waiting_to_connected_flow()
{
    ping_result = true;
    delay(510);
    TyrantConnection::update();

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantConnection::State::AGENT_AVAILABLE),
        static_cast<uint8_t>(TyrantConnection::getState()));

    TyrantConnection::update();

    TEST_ASSERT_TRUE(TyrantConnection::connected());
    TEST_ASSERT_TRUE(TyrantSafety::transportConnected());
    TEST_ASSERT_EQUAL_UINT32(1, TyrantConnection::getStats().connection_count);
}

void test_entity_creation_failure_returns_to_waiting()
{
    ping_result = true;
    create_result = false;
    delay(510);
    TyrantConnection::update();
    TyrantConnection::update();

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantConnection::State::WAITING_AGENT),
        static_cast<uint8_t>(TyrantConnection::getState()));
    TEST_ASSERT_FALSE(TyrantSafety::transportConnected());
    TEST_ASSERT_GREATER_THAN_UINT32(0, destroy_calls);
}

void test_disconnect_and_reconnect_updates_stats()
{
    ping_result = true;
    delay(510);
    TyrantConnection::update();
    TyrantConnection::update();
    TEST_ASSERT_TRUE(TyrantConnection::connected());

    ping_result = false;
    delay(510);
    TyrantConnection::update();

    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantConnection::State::DISCONNECTED),
        static_cast<uint8_t>(TyrantConnection::getState()));
    TEST_ASSERT_FALSE(TyrantSafety::transportConnected());
    TEST_ASSERT_EQUAL_UINT32(1, TyrantConnection::getStats().disconnect_count);

    TyrantConnection::update();
    TEST_ASSERT_EQUAL_UINT8(
        static_cast<uint8_t>(TyrantConnection::State::WAITING_AGENT),
        static_cast<uint8_t>(TyrantConnection::getState()));

    ping_result = true;
    delay(510);
    TyrantConnection::update();
    TyrantConnection::update();

    const auto stats = TyrantConnection::getStats();
    TEST_ASSERT_TRUE(TyrantConnection::connected());
    TEST_ASSERT_EQUAL_UINT32(2, stats.connection_count);
    TEST_ASSERT_EQUAL_UINT32(1, stats.reconnect_count);
}

void setup()
{
    delay(500);
    UNITY_BEGIN();
    RUN_TEST(test_starts_waiting_for_agent);
    RUN_TEST(test_waiting_to_connected_flow);
    RUN_TEST(test_entity_creation_failure_returns_to_waiting);
    RUN_TEST(test_disconnect_and_reconnect_updates_stats);
    UNITY_END();
}

void loop() {}
