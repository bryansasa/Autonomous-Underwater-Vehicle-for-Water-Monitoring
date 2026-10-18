#include "vehicle/vehicle_mode.h"

namespace
{
    TyrantVehicle::Mode current_mode =
        TyrantVehicle::Mode::BOOT;

    TyrantVehicle::TransitionResult accepted()
    {
        return {
            true,
            TyrantVehicle::Reason::REQUEST_ACCEPTED
        };
    }

    TyrantVehicle::TransitionResult rejected(
        TyrantVehicle::Reason reason
    )
    {
        return {
            false,
            reason
        };
    }
}

namespace TyrantVehicle
{
    void init()
    {
        current_mode = Mode::BOOT;
    }

    void completeBoot(bool initialization_ok)
    {
        if (initialization_ok)
        {
            current_mode = Mode::IDLE;
        }
        else
        {
            current_mode = Mode::FAULT;
        }
    }

    TransitionResult requestMode(
        Mode requested_mode,
        bool system_healthy,
        bool autonomy_ready
    )
    {
        if (current_mode == Mode::EMERGENCY)
        {
            return rejected(
                Reason::EMERGENCY_LATCHED
            );
        }

        if (current_mode == Mode::FAULT)
        {
            return rejected(
                Reason::FAULT_LATCHED
            );
        }

        if (requested_mode == current_mode)
        {
            return accepted();
        }

        // Host cannot directly command these states.
        if (
            requested_mode == Mode::BOOT ||
            requested_mode == Mode::FAULT ||
            requested_mode == Mode::EMERGENCY
        )
        {
            return rejected(
                Reason::TRANSITION_NOT_ALLOWED
            );
        }

        // SAFE may always be requested.
        if (requested_mode == Mode::SAFE)
        {
            current_mode = Mode::SAFE;
            return accepted();
        }

        switch (current_mode)
        {
            case Mode::BOOT:
            {
                return rejected(
                    Reason::TRANSITION_NOT_ALLOWED
                );
            }

            case Mode::IDLE:
            {
                if (requested_mode == Mode::MANUAL)
                {
                    if (!system_healthy)
                    {
                        return rejected(
                            Reason::SYSTEM_UNHEALTHY
                        );
                    }

                    current_mode = Mode::MANUAL;
                    return accepted();
                }

                if (requested_mode == Mode::AUTO)
                {
                    if (!system_healthy)
                    {
                        return rejected(
                            Reason::SYSTEM_UNHEALTHY
                        );
                    }

                    if (!autonomy_ready)
                    {
                        return rejected(
                            Reason::AUTONOMY_NOT_READY
                        );
                    }

                    current_mode = Mode::AUTO;
                    return accepted();
                }

                return rejected(
                    Reason::TRANSITION_NOT_ALLOWED
                );
            }

            case Mode::MANUAL:
            {
                if (requested_mode == Mode::IDLE)
                {
                    current_mode = Mode::IDLE;
                    return accepted();
                }

                return rejected(
                    Reason::TRANSITION_NOT_ALLOWED
                );
            }

            case Mode::AUTO:
            {
                if (requested_mode == Mode::IDLE)
                {
                    current_mode = Mode::IDLE;
                    return accepted();
                }

                return rejected(
                    Reason::TRANSITION_NOT_ALLOWED
                );
            }

            case Mode::SAFE:
            {
                if (requested_mode == Mode::IDLE)
                {
                    if (!system_healthy)
                    {
                        return rejected(
                            Reason::SYSTEM_UNHEALTHY
                        );
                    }

                    current_mode = Mode::IDLE;
                    return accepted();
                }

                return rejected(
                    Reason::TRANSITION_NOT_ALLOWED
                );
            }

            case Mode::FAULT:
            case Mode::EMERGENCY:
            default:
            {
                return rejected(
                    Reason::TRANSITION_NOT_ALLOWED
                );
            }
        }
    }

    void forceSafe()
    {
        if (
            current_mode != Mode::FAULT &&
            current_mode != Mode::EMERGENCY
        )
        {
            current_mode = Mode::SAFE;
        }
    }

    void forceFault()
    {
        if (current_mode != Mode::EMERGENCY)
        {
            current_mode = Mode::FAULT;
        }
    }

    void forceEmergency()
    {
        current_mode = Mode::EMERGENCY;
    }

    Mode getMode()
    {
        return current_mode;
    }
}
