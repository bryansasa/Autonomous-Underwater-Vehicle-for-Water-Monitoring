#include "safety/safety_manager.h"
#include "vehicle/vehicle_mode.h"

namespace
{
    bool transport_connected = false;

    bool host_heartbeat_received = false;
    unsigned long last_host_heartbeat_ms = 0;

    constexpr unsigned long HOST_TIMEOUT_MS = 500;

    bool internal_mode_event = false;

    bool autonomy_ready_signal = false;

    uint8_t internal_mode_reason =
        static_cast<uint8_t>(
            TyrantVehicle::Reason::NONE
        );


    void registerCommunicationTimeout()
    {
        internal_mode_event = true;

        internal_mode_reason =
            static_cast<uint8_t>(
                TyrantVehicle::Reason::
                    COMMUNICATION_TIMEOUT
            );
    }
}


namespace TyrantSafety
{
    void init()
    {
        transport_connected = false;

        host_heartbeat_received = false;
        last_host_heartbeat_ms = 0;

        internal_mode_event = false;
        autonomy_ready_signal = false;

        internal_mode_reason =
            static_cast<uint8_t>(
                TyrantVehicle::Reason::NONE
            );

        TyrantVehicle::init();

        // Bring-up self test currently considered OK.
        TyrantVehicle::completeBoot(true);
    }


    void setTransportConnected(bool connected)
    {
        transport_connected = connected;

        if (!connected)
        {
            host_heartbeat_received = false;
            last_host_heartbeat_ms = 0;

            const TyrantVehicle::Mode mode =
                TyrantVehicle::getMode();

            if (
                mode == TyrantVehicle::Mode::MANUAL ||
                mode == TyrantVehicle::Mode::AUTO
            )
            {
                TyrantVehicle::forceSafe();

                registerCommunicationTimeout();
            }
        }
    }


    bool transportConnected()
    {
        return transport_connected;
    }


    void notifyHostHeartbeat()
    {
        if (!transport_connected)
        {
            return;
        }

        host_heartbeat_received = true;

        last_host_heartbeat_ms =
            millis();
    }


    bool communicationHealthy()
    {
        if (!transport_connected)
        {
            return false;
        }

        if (!host_heartbeat_received)
        {
            return false;
        }

        const unsigned long now =
            millis();

        return (
            now - last_host_heartbeat_ms
            <= HOST_TIMEOUT_MS
        );
    }


    bool systemHealthy()
    {
        return communicationHealthy();
    }


    void setAutonomyReady(bool ready)
    {
        autonomy_ready_signal = ready;
    }


    bool autonomyReady()
    {
        return communicationHealthy() && autonomy_ready_signal;
    }


    ModeRequestResult requestMode(
        uint8_t requested_mode
    )
    {
        if (requested_mode > 6)
        {
            return {
                false,
                static_cast<uint8_t>(
                    TyrantVehicle::Reason::
                        INVALID_MODE
                )
            };
        }

        const auto result =
            TyrantVehicle::requestMode(
                static_cast<
                    TyrantVehicle::Mode
                >(requested_mode),
                systemHealthy(),
                autonomyReady()
            );

        return {
            result.accepted,
            static_cast<uint8_t>(
                result.reason
            )
        };
    }


    void update()
    {
        const TyrantVehicle::Mode mode =
            TyrantVehicle::getMode();

        if (
            mode == TyrantVehicle::Mode::MANUAL ||
            mode == TyrantVehicle::Mode::AUTO
        )
        {
            if (!communicationHealthy())
            {
                TyrantVehicle::forceSafe();

                registerCommunicationTimeout();
            }
        }
    }


    uint8_t getMode()
    {
        return static_cast<uint8_t>(
            TyrantVehicle::getMode()
        );
    }


    bool propulsionAllowed()
    {
        if (!systemHealthy())
        {
            return false;
        }

        const TyrantVehicle::Mode mode =
            TyrantVehicle::getMode();

        if (
            mode == TyrantVehicle::Mode::MANUAL
        )
        {
            return true;
        }

        if (
            mode == TyrantVehicle::Mode::AUTO &&
            autonomyReady()
        )
        {
            return true;
        }

        return false;
    }




    bool emergencyActuationAllowed()
    {
        return TyrantVehicle::getMode() == TyrantVehicle::Mode::EMERGENCY;
    }


    void forceSafe()
    {
        TyrantVehicle::forceSafe();
    }


    void triggerEmergency()
    {
        TyrantVehicle::forceEmergency();
    }


    bool takeInternalModeEvent(
        uint8_t &reason
    )
    {
        if (!internal_mode_event)
        {
            return false;
        }

        reason = internal_mode_reason;

        internal_mode_event = false;

        return true;
    }
   uint32_t hostHeartbeatAgeMs()
    {
    if (!host_heartbeat_received)
    {
        return 0xFFFFFFFFu;
    }

    const unsigned long now =
        millis();

    return static_cast<uint32_t>(
        now - last_host_heartbeat_ms
    );
    }
}
