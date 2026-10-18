#pragma once

#include <Arduino.h>


namespace TyrantSafety
{
    struct ModeRequestResult
    {
        bool accepted;
        uint8_t reason;
    };


    void init();


    void update();


    void setTransportConnected(
        bool connected
    );


    void notifyHostHeartbeat();


    ModeRequestResult requestMode(
        uint8_t requested_mode
    );


    uint8_t getMode();


    bool transportConnected();


    bool communicationHealthy();


    uint32_t hostHeartbeatAgeMs();


    bool systemHealthy();


    void setAutonomyReady(bool ready);


    bool autonomyReady();


    bool propulsionAllowed();


    bool emergencyActuationAllowed();


    void forceSafe();


    void triggerEmergency();


    bool takeInternalModeEvent(
        uint8_t &reason
    );
}