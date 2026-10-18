#pragma once

#include <Arduino.h>

namespace TyrantScheduler
{
    void init();

    bool heartbeatDue();

    bool healthDue();

    bool safetyDue();

    bool controlDue();
}
