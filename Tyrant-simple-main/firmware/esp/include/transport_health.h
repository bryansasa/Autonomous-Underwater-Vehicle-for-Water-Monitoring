#pragma once
#include <stdint.h>
#include "payload_config.h"
// Keep transient serial/host scheduling delays separate from sustained loss.
class TransportHealth {
public:
    void reset() { missed_probes_=0; publish_failure_seen_=false; }
    bool probeFailed() {
        if (missed_probes_ < PayloadConfig::AGENT_MISSED_PROBES) ++missed_probes_;
        return missed_probes_ >= PayloadConfig::AGENT_MISSED_PROBES;
    }
    void probeSucceeded() { missed_probes_=0; }
    void publishResult(bool success, uint32_t now_ms) {
        if (success) publish_failure_seen_=false;
        else if (!publish_failure_seen_) {
            publish_failure_seen_=true; first_publish_failure_ms_=now_ms;
        }
    }
    bool publishingStalled(uint32_t now_ms) const {
        return publish_failure_seen_ &&
            static_cast<uint32_t>(now_ms-first_publish_failure_ms_) >= PayloadConfig::PUBLISH_FAILURE_GRACE_MS;
    }
private:
    uint8_t missed_probes_=0;
    bool publish_failure_seen_=false;
    uint32_t first_publish_failure_ms_=0;
};
