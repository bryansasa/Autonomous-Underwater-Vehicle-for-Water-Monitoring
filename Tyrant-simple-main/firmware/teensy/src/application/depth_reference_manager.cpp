#include "application/depth_reference_manager.h"

#include "safety/safety_manager.h"

#include "sensors/sensor_manager.h"

#include "vehicle/vehicle_mode.h"


namespace
{
    // ========================================================
    // DEPTH REFERENCE COMMANDS
    //
    // Values intentionally match:
    // tyrant_interfaces/msg/DepthReferenceRequest.msg
    // ========================================================

    enum class Command : uint8_t
    {
        SET_SURFACE = 1,

        CLEAR_REFERENCE = 2
    };


    // ========================================================
    // BUILD RESULT
    // ========================================================

    TyrantDepthReference::Result makeResult(
        bool accepted,
        TyrantDepthReference::Reason reason
    )
    {
        const bool reference_valid =
            TyrantSensors::
                depthSurfaceReferenceValid();


        const float surface_pressure_pa =
            reference_valid
                ? TyrantSensors::
                    depthSurfacePressurePa()
                : 0.0f;


        return {
            accepted,
            reason,
            reference_valid,
            surface_pressure_pa
        };
    }
}


namespace TyrantDepthReference
{
    Result handleRequest(
        uint8_t command
    )
    {
        // ====================================================
        // VALIDATE COMMAND
        // ====================================================

        const bool command_valid =
            command ==
                static_cast<uint8_t>(
                    Command::SET_SURFACE
                )
            ||
            command ==
                static_cast<uint8_t>(
                    Command::CLEAR_REFERENCE
                );


        if (!command_valid)
        {
            return makeResult(
                false,
                Reason::INVALID_COMMAND
            );
        }


        // ====================================================
        // VEHICLE MODE POLICY
        //
        // Depth reference may only be modified while IDLE.
        // ====================================================

        if (
            TyrantSafety::getMode() !=
                static_cast<uint8_t>(
                    TyrantVehicle::Mode::IDLE
                )
        )
        {
            return makeResult(
                false,
                Reason::VEHICLE_NOT_IDLE
            );
        }


        // ====================================================
        // CLEAR REFERENCE
        // ====================================================

        if (
            command ==
                static_cast<uint8_t>(
                    Command::CLEAR_REFERENCE
                )
        )
        {
            TyrantSensors::
                clearDepthSurfaceReference();


            return makeResult(
                true,
                Reason::REQUEST_ACCEPTED
            );
        }


        // ====================================================
        // SET SURFACE REFERENCE
        // ====================================================

        const auto pressure_health =
            TyrantSensors::
                getPressureHealth();


        if (
            pressure_health.state !=
                TyrantSensors::
                    SensorState::READY
        )
        {
            return makeResult(
                false,
                Reason::PRESSURE_NOT_READY
            );
        }


        if (!pressure_health.valid)
        {
            return makeResult(
                false,
                Reason::PRESSURE_INVALID
            );
        }


        if (
            !TyrantSensors::
                setDepthSurfaceReference()
        )
        {
            return makeResult(
                false,
                Reason::SET_REFERENCE_FAILED
            );
        }


        return makeResult(
            true,
            Reason::REQUEST_ACCEPTED
        );
    }
}