#include <Arduino.h>
#include <unity.h>

#include "scheduler/scheduler.h"

void test_periods_fire_at_expected_order()
{
    TyrantScheduler::init();

    TEST_ASSERT_FALSE(TyrantScheduler::controlDue());
    TEST_ASSERT_FALSE(TyrantScheduler::safetyDue());
    TEST_ASSERT_FALSE(TyrantScheduler::healthDue());
    TEST_ASSERT_FALSE(TyrantScheduler::heartbeatDue());

    delay(25);
    TEST_ASSERT_TRUE(TyrantScheduler::controlDue());
    TEST_ASSERT_FALSE(TyrantScheduler::safetyDue());

    delay(85);
    TEST_ASSERT_TRUE(TyrantScheduler::safetyDue());
    TEST_ASSERT_FALSE(TyrantScheduler::healthDue());

    delay(100);
    TEST_ASSERT_TRUE(TyrantScheduler::healthDue());
    TEST_ASSERT_FALSE(TyrantScheduler::heartbeatDue());

    delay(800);
    TEST_ASSERT_TRUE(TyrantScheduler::heartbeatDue());
}

void test_due_call_resets_its_own_period()
{
    TyrantScheduler::init();
    delay(25);
    TEST_ASSERT_TRUE(TyrantScheduler::controlDue());
    TEST_ASSERT_FALSE(TyrantScheduler::controlDue());
    delay(25);
    TEST_ASSERT_TRUE(TyrantScheduler::controlDue());
}

void setup()
{
    delay(500);
    UNITY_BEGIN();
    RUN_TEST(test_periods_fire_at_expected_order);
    RUN_TEST(test_due_call_resets_its_own_period);
    UNITY_END();
}

void loop() {}
