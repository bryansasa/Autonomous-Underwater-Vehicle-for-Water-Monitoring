#include "communication/connection_manager.h"

#include "communication/ros_interface.h"
#include "safety/safety_manager.h"

namespace
{
    TyrantConnection::State current_state =
        TyrantConnection::State::WAITING_AGENT;

    unsigned long last_waiting_ping_ms = 0;
    unsigned long last_connected_ping_ms = 0;
    uint32_t connection_count = 0;
    uint32_t disconnect_count = 0;
    uint32_t reconnect_count = 0;

    constexpr unsigned long WAITING_PING_PERIOD_MS = 500;
    constexpr unsigned long CONNECTED_PING_PERIOD_MS = 500;

    constexpr uint32_t PING_TIMEOUT_MS = 50;
    constexpr uint8_t PING_ATTEMPTS = 1;
}

namespace TyrantConnection
{
    void init()
    {
        current_state = State::WAITING_AGENT;

        last_waiting_ping_ms = 0;
        last_connected_ping_ms = 0;
        connection_count = 0;
        disconnect_count = 0;
        reconnect_count = 0;

        TyrantSafety::setTransportConnected(false);
    }


    void update()
    {
        const unsigned long now = millis();

        switch (current_state)
        {
            // =================================================
            // AGENT BELUM ADA
            // =================================================

            case State::WAITING_AGENT:
            {
                if (
                    now - last_waiting_ping_ms
                    < WAITING_PING_PERIOD_MS
                )
                {
                    break;
                }

                last_waiting_ping_ms = now;

                if (
                    TyrantROS::pingAgent(
                        PING_TIMEOUT_MS,
                        PING_ATTEMPTS
                    )
                )
                {
                    current_state =
                        State::AGENT_AVAILABLE;
                }

                break;
            }


            // =================================================
            // AGENT DITEMUKAN, BUAT ROS ENTITIES
            // =================================================

            case State::AGENT_AVAILABLE:
            {
                if (TyrantROS::createEntities())
                {
                    connection_count++;

                    if (connection_count > 1)
                    {
                        reconnect_count++;
                    }

                    TyrantSafety::setTransportConnected(true);

                    last_connected_ping_ms = millis();

                    current_state =
                        State::CONNECTED;
                }
                else
                {
                    TyrantROS::destroyEntities();

                    TyrantSafety::setTransportConnected(false);

                    current_state =
                        State::WAITING_AGENT;
                }

                break;
            }


            // =================================================
            // NORMAL OPERATION
            // =================================================

            case State::CONNECTED:
            {
                TyrantROS::spin();

                if (
                    now - last_connected_ping_ms
                    >= CONNECTED_PING_PERIOD_MS
                )
                {
                    last_connected_ping_ms = now;

                    if (
                        !TyrantROS::pingAgent(
                            PING_TIMEOUT_MS,
                            PING_ATTEMPTS
                        )
                    )
                    {
                        disconnect_count++;
                        // Safety is informed immediately.
                        TyrantSafety::setTransportConnected(false);

                        current_state =
                            State::DISCONNECTED;
                    }
                }

                break;
            }


            // =================================================
            // CONNECTION LOST
            // =================================================

            case State::DISCONNECTED:
            {
                TyrantROS::destroyEntities();

                current_state =
                    State::WAITING_AGENT;

                last_waiting_ping_ms = millis();

                break;
            }


            default:
            {
                TyrantSafety::setTransportConnected(false);

                TyrantROS::destroyEntities();

                current_state =
                    State::WAITING_AGENT;

                break;
            }
        }
    }


    bool connected()
    {
        return current_state ==
            State::CONNECTED;
    }

    State getState()
        {
            return current_state;
        }


        Stats getStats()
        {
            return {
                connection_count,
                disconnect_count,
                reconnect_count
            };
        }
}
