#pragma once

#include <Arduino.h>

namespace TyrantVehicle
{
    enum class Mode : uint8_t
    {
        BOOT = 0,
        IDLE = 1,
        MANUAL = 2,
        AUTO = 3,
        SAFE = 4,
        FAULT = 5,
        EMERGENCY = 6
    };

    enum class Reason : uint8_t
    {
        NONE = 0,
        REQUEST_ACCEPTED = 1,
        INVALID_MODE = 2,
        TRANSITION_NOT_ALLOWED = 3,
        SYSTEM_UNHEALTHY = 4,
        AUTONOMY_NOT_READY = 5,
        COMMUNICATION_TIMEOUT = 6,
        FAULT_LATCHED = 7,
        EMERGENCY_LATCHED = 8
    };

    struct TransitionResult
    {
        bool accepted;
        Reason reason;
    };

    void init();

    void completeBoot(bool initialization_ok);

    TransitionResult requestMode(
        Mode requested_mode,
        bool system_healthy,
        bool autonomy_ready
    );

    void forceSafe();
    void forceFault();
    void forceEmergency();

    Mode getMode();
}
