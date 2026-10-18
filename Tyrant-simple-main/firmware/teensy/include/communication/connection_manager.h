#pragma once

#include <Arduino.h>

namespace TyrantConnection
{
    enum class State : uint8_t
    {
        WAITING_AGENT = 0,
        AGENT_AVAILABLE,
        CONNECTED,
        DISCONNECTED
    };


    struct Stats
    {
        uint32_t connection_count;
        uint32_t disconnect_count;
        uint32_t reconnect_count;
    };


    void init();

    void update();

    bool connected();

    State getState();

    Stats getStats();
}
