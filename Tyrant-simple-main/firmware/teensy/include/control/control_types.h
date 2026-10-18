#pragma once

#include <Arduino.h>

namespace TyrantControl
{
    struct ManualCommand
    {
        uint32_t sequence = 0;

        float surge = 0.0f;
        float sway = 0.0f;
        float heave = 0.0f;

        float roll = 0.0f;
        float pitch = 0.0f;
        float yaw = 0.0f;
    };

    struct WrenchRequest
    {
        uint32_t source_sequence = 0;

        // Normalized body-FRD wrench request in [-1, +1].
        // These are intentionally dimensionless at this stage.
        float x = 0.0f;
        float y = 0.0f;
        float z = 0.0f;

        float k = 0.0f;
        float m = 0.0f;
        float n = 0.0f;

        bool command_fresh = false;
        bool enabled = false;
    };
}
