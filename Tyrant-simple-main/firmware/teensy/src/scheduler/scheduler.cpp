#include "scheduler/scheduler.h"

namespace
{
    unsigned long last_heartbeat_ms = 0;
    unsigned long last_health_ms = 0;
    unsigned long last_safety_ms = 0;
    unsigned long last_control_ms = 0;

    constexpr unsigned long HEARTBEAT_PERIOD_MS = 1000;
    constexpr unsigned long HEALTH_PERIOD_MS = 200;
    constexpr unsigned long SAFETY_PERIOD_MS = 100;
    constexpr unsigned long CONTROL_PERIOD_MS = 20;
}

namespace TyrantScheduler
{
    void init()
    {
        const unsigned long now = millis();

        last_heartbeat_ms = now;
        last_health_ms = now;
        last_safety_ms = now;
        last_control_ms = now;
    }

    bool heartbeatDue()
    {
        const unsigned long now = millis();

        if (
            now - last_heartbeat_ms >=
            HEARTBEAT_PERIOD_MS
        )
        {
            last_heartbeat_ms = now;
            return true;
        }

        return false;
    }

    bool healthDue()
    {
        const unsigned long now = millis();

        if (
            now - last_health_ms >=
            HEALTH_PERIOD_MS
        )
        {
            last_health_ms = now;
            return true;
        }

        return false;
    }

    bool safetyDue()
    {
        const unsigned long now = millis();

        if (
            now - last_safety_ms >=
            SAFETY_PERIOD_MS
        )
        {
            last_safety_ms = now;
            return true;
        }

        return false;
    }

    bool controlDue()
    {
        const unsigned long now = millis();

        if (
            now - last_control_ms >=
            CONTROL_PERIOD_MS
        )
        {
            last_control_ms = now;
            return true;
        }

        return false;
    }
}
