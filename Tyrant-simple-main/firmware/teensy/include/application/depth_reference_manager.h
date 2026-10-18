#pragma once

#include <stdint.h>


namespace TyrantDepthReference
{
    // ========================================================
    // RESULT REASONS
    //
    // Values intentionally match:
    // tyrant_interfaces/msg/DepthReferenceStatus.msg
    // ========================================================

    enum class Reason : uint8_t
    {
        NONE = 0,

        REQUEST_ACCEPTED = 1,

        INVALID_COMMAND = 2,

        VEHICLE_NOT_IDLE = 3,

        PRESSURE_NOT_READY = 4,

        PRESSURE_INVALID = 5,

        SET_REFERENCE_FAILED = 6
    };


    // ========================================================
    // REQUEST RESULT
    // ========================================================

    struct Result
    {
        bool accepted;

        Reason reason;

        bool reference_valid;

        float surface_pressure_pa;
    };


    // ========================================================
    // APPLICATION POLICY
    // ========================================================

    Result handleRequest(
        uint8_t command
    );
}